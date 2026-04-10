"""
12306 抢票助手 - NiceGUI 界面逻辑 (融入原版硬核策略与配置兼容)
"""
import os
import json
import time
import threading
import urllib.request as r
from datetime import datetime, timedelta
from nicegui import ui

# 导入同目录下的 Getticket 模块
from app.getticket import GetTicket

class ConfigManager:
    """配置管理类 - 从config.json加载系统配置，并处理12306数据字典"""
    def __init__(self):
        self._load_config()
        self.CITYCODE = self._get_city_codes()
        self.month_dict = {
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
        }

    def _load_config(self):
        """从 config.json 加载配置，兼容根目录位置"""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        config_path = os.path.join(base_dir, "config.json")

        if not os.path.exists(config_path):
            config_path = "config.json"

        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                self.max_try_times = config.get("max_try_times", 3)
                self.logswitch = config.get("logswitch", False)
                self.ischoose_position = config.get("ischoose_position", True)
                self.advanced = config.get("advanced", 0.0)
                self.adjust_times_max = config.get("adjust_times_max", 80)
                self.grabfunction_max_try_times = config.get("grabfunction_max_try_times", 6)
            except Exception as e:
                print(f"加载配置文件失败: {e}，使用默认配置")
                self._set_default_config()
        else:
            self._set_default_config()

    def _set_default_config(self):
        """设置默认配置"""
        self.max_try_times = 3
        self.logswitch = False
        self.ischoose_position = True
        self.advanced = 0.0
        self.adjust_times_max = 80
        self.grabfunction_max_try_times = 6

    def _get_city_codes(self):
        """获取最新的全国车站三字码"""
        code_url = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js"
        try:
            req = r.Request(code_url, headers={'User-Agent': 'Mozilla/5.0'})
            with r.urlopen(req, timeout=10) as response:
                code_data = response.read().decode('utf-8')
            city_codes = self._zip_dic(code_data)
            print(f"成功从12306加载站点数据，共{len(city_codes)}个车站")
            return city_codes
        except Exception as e:
            print(f"获取站点三字码失败: {e}，将使用内置示例车站数据")
            return {
                '北京南': 'VNP', '北京北': 'VAP', '北京西': 'BXP', '北京': 'BJP',
                '上海虹桥': 'AOH', '上海南': 'SNH', '上海': 'SHH',
                '广州南': 'IZQ', '广州': 'GZQ', '深圳北': 'IOQ', '深圳': 'SZQ',
                '武汉': 'WHN', '汉口': 'HKN', '南京南': 'NKH', '南京': 'NJH',
                '杭州东': 'HGH', '杭州': 'HZH', '成都东': 'ICW', '成都': 'CDW',
                '重庆北': 'CUW', '重庆': 'CQW', '西安北': 'EAY', '西安': 'XAY',
                '天津': 'TJP', '沈阳北': 'SBT', '哈尔滨西': 'VAB'
            }

    def _zip_dic(self, code_data):
        import re
        # 使用正则表达式精确提取，避免 12306 数据结构无分隔符导致的错位
        matches = re.findall(r'\|([^|]+)\|([A-Z]{3})\|', code_data)

        city_codes = {}
        for name, code in matches:
            city_codes[name] = code

        return city_codes

    def load_from_dict(self, data):
        """动态将UI表单的配置注入到 config 实例中"""
        for key, value in data.items():
            setattr(self, key, value)

# 票类代码映射
TICKET_CLASS_CODES = {
    "二等座": "O", "一等座": "M", "商务座": "9", "特等座": "P",
    "一等卧": "I", "二等卧": "J", "硬卧": "3", "软卧": "4",
    "动卧": "F", "硬座": "1", "软座": "2", "高级动卧": "A", "高级软卧": "6"
}

# 乘客类型映射 (修改为兼容原版配置文件)
PASSENGER_CLASS_CODES = {
    "成人": "1", "儿童": "2", "学生": "3", "残军": "4"
}

# 位置选项
POSITION_OPTIONS = {
    "不限": "",
    "A (靠窗)": "A", "B (中间)": "B", "C (过道)": "C",
    "D (过道)": "D", "F (靠窗)": "F",
    "上铺": "上铺", "中铺": "中铺", "下铺": "下铺"
}

class WebApp:
    def __init__(self):
        self.config = ConfigManager()
        self.get_ticket = GetTicket(self.config)
        self.logged_in = False
        self.task_running = False
        self.users_data = {}
        self.current_qr_uuid = None

        self.qr_timer_active = False
        self.log_timer_active = False
        self.last_log_index = 0
        self.pending_notifs = []

        # 联动控制标志
        self.updating_stations = False
        self.updating_city = False

        os.makedirs("data", exist_ok=True)
        self.load_users_data()
        self.create_ui()

    def load_users_data(self):
        users_file = "data/user_data.json"
        if os.path.exists(users_file):
            try:
                with open(users_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    config_keys = {'train_date', 'TICKET_CLASS', 'NAME', 'ID'}
                    if data.keys() & config_keys:
                        username = data.get('NAME', '默认用户') or '默认用户'
                        self.users_data = {username: data}
                        self.save_users_data()
                    else:
                        self.users_data = data
                else:
                    self.users_data = {}
            except Exception as e:
                print(f"加载用户数据失败: {e}")
                self.users_data = {}
        else:
            self.users_data = {}

    def save_users_data(self):
        try:
            with open("data/user_data.json", "w", encoding="utf-8") as f:
                json.dump(self.users_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存用户数据失败: {e}")

    def create_ui(self):
        ui.add_head_html("""
        <style>
            body { background-color: #f3f4f6; }
            .nicegui-content { background-color: transparent !important; padding: 0 !important; }
            .terminal-log, .terminal-log textarea { 
                border: none !important; 
                box-shadow: none !important; 
                outline: none !important; 
            }
            .terminal-log::-webkit-scrollbar { width: 8px; }
            .terminal-log::-webkit-scrollbar-track { background: #0f172a; }
            .terminal-log::-webkit-scrollbar-thumb { background: #4b5563; border-radius: 4px; }
            .q-field__control { border-radius: 8px !important; }
        </style>
        """)

        # --- 顶部导航栏 ---
        with ui.header().classes('bg-indigo-700 text-white p-3 shadow-lg flex justify-between items-center w-full'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('train', size='md')
                ui.label('12306 极速抢票助手').classes('text-xl font-extrabold tracking-wide')

            with ui.row().classes('items-center gap-4'):
                self.login_status_badge = ui.badge('○ 未登录', color='red-5').classes('text-sm px-2 py-1')
                ui.button('扫码登录', icon='qr_code_scanner', on_click=self.get_qr_code).props('flat text-color=white')
                ui.button(icon='refresh', on_click=self.check_login_status).props('flat round text-color=white').tooltip('刷新登录状态')
                ui.button(icon='manage_accounts', on_click=self.show_user_management).props('flat round text-color=white').tooltip('用户账号配置')

        # --- 核心主界面布局 ---
        with ui.row().classes('w-full max-w-[1400px] mx-auto gap-6 p-6 items-stretch flex-wrap lg:flex-nowrap'):

            # 【左侧区块】：行程参数 & 乘客信息
            with ui.column().classes('w-full lg:w-2/3 flex flex-col gap-6'):

                # 1. 行程配置卡片
                with ui.card().classes('w-full shadow-md rounded-xl p-5 bg-white'):
                    with ui.row().classes('items-center mb-4 text-indigo-700'):
                        ui.icon('map', size='sm')
                        ui.label('行程配置').classes('text-lg font-bold ml-2')

                with ui.grid(columns=1).classes('w-full md:grid-cols-2 gap-4'):
                    with ui.column().classes('w-full gap-2'):
                        self.start_city_input = ui.input('出发城市', placeholder='如: 北京',
                                                         on_change=lambda e: self.update_stations('start')).classes(
                            'w-full').props('outlined dense')
                        self.start_station_select = ui.select(options=['请选择'], label='出发车站', value='请选择',
                                                              on_change=lambda e: self.on_station_change(
                                                                  'start')).classes('w-full').props(
                            'outlined dense options-dense')

                    with ui.column().classes('w-full gap-2'):
                        self.end_city_input = ui.input('到达城市', placeholder='如: 上海',
                                                       on_change=lambda e: self.update_stations('end')).classes(
                            'w-full').props('outlined dense')
                        self.end_station_select = ui.select(options=['请选择'], label='到达车站', value='请选择',
                                                            on_change=lambda e: self.on_station_change(
                                                                'end')).classes('w-full').props(
                            'outlined dense options-dense')
                    ui.separator().classes('my-4')
                    with ui.grid(columns=1).classes('w-full md:grid-cols-2 gap-4'):
                        self.train_date_input = ui.input('乘车日期').classes('w-full').props('outlined dense type=date')
                        self.train_list_input = ui.input('期望车次', placeholder='逗号分隔, 如: G1,G102').classes('w-full').props('outlined dense')

                # 2. 乘客信息卡片
                with ui.card().classes('w-full shadow-md rounded-xl p-5 bg-white'):
                    with ui.row().classes('items-center mb-4 text-indigo-700'):
                        ui.icon('badge', size='sm')
                        ui.label('乘客与席别').classes('text-lg font-bold ml-2')

                    with ui.grid(columns=1).classes('w-full md:grid-cols-3 gap-4'):
                        self.name_input = ui.input('姓名').classes('w-full').props('outlined dense')
                        self.gender_select = ui.select(['男', '女'], value='男', label='性别').classes('w-full').props('outlined dense options-dense')
                        # 修改默认值为 '成人'
                        self.passenger_class_select = ui.select(list(PASSENGER_CLASS_CODES.keys()), value='成人', label='票种').classes('w-full').props('outlined dense options-dense')

                    with ui.grid(columns=1).classes('w-full md:grid-cols-2 gap-4 mt-4'):
                        self.id_input = ui.input('身份证号').classes('w-full').props('outlined dense')
                        self.phone_input = ui.input('手机号').classes('w-full').props('outlined dense')

                    with ui.grid(columns=1).classes('w-full md:grid-cols-2 gap-4 mt-4'):
                        self.ticket_class_select = ui.select(list(TICKET_CLASS_CODES.keys()), value='二等座', label='优先席别', on_change=self.filter_position_options).classes('w-full').props('outlined dense options-dense')
                        self.position_select = ui.select(list(POSITION_OPTIONS.keys()), value='不限', label='位置偏好').classes('w-full').props('outlined dense options-dense')

            # 【右侧区块】：启动控制台 & 运行日志
            with ui.column().classes('w-full lg:w-1/3 flex flex-col gap-6'):

                # 3. 抢票中枢
                with ui.card().classes('w-full shadow-md rounded-xl p-5 bg-white flex flex-col flex-grow'):
                    with ui.row().classes('items-center mb-4 text-indigo-700 justify-between w-full'):
                        with ui.row().classes('items-center'):
                            ui.icon('rocket_launch', size='sm')
                            ui.label('任务控制台').classes('text-lg font-bold ml-2')
                        self.task_status_label = ui.label('待命').classes('text-gray-500 font-bold text-sm bg-gray-100 px-2 py-1 rounded')

                    with ui.row().classes('w-full items-center gap-2 mb-4'):
                        self.start_time_input = ui.input('定时开抢 (留空立即执行)', placeholder='YYYY-MM-DD HH:MM:SS').classes('flex-grow').props('outlined dense')
                        ui.button(icon='my_location', on_click=self.set_current_time).props('flat round color=primary').tooltip('同步当前系统时间')

                    self.start_btn = ui.button('立即启动抢票', on_click=self.start_grab_task).classes('w-full py-3 text-lg font-bold rounded-lg shadow-md mb-2').props('color=red-6 push icon=bolt')

                    ui.separator().classes('my-2')

                    with ui.row().classes('w-full justify-between items-center mb-2 mt-2'):
                        ui.label('终端日志').classes('font-bold text-gray-700 text-sm')
                        ui.button(icon='delete_sweep', on_click=self.clear_logs).props('flat round size=sm color=grey').tooltip('清空日志')

                    with ui.element('div').classes('w-full flex-1 min-h-[350px] flex flex-col rounded-lg overflow-hidden border border-gray-800 shadow-inner bg-[#0f172a]'):
                        self.log_output = ui.log().classes(
                            'terminal-log w-full flex-1 bg-transparent text-green-400 font-mono text-sm '
                            'whitespace-pre-wrap break-words p-4 border-none outline-none ring-0 m-0'
                        )

        # 挂载定时器
        self.log_timer = ui.timer(1, self.poll_logs)
        self.log_timer_active = True

        # 初始化对话框
        self.create_qr_dialog()
        self.create_user_management_dialog()
        self.filter_position_options()

    def get_login_status_class(self):
        return 'green-5' if self.logged_in else 'red-5'

    def update_login_status_display(self):
        self.login_status_badge.text = '● 已登录' if self.logged_in else '○ 未登录'
        self.login_status_badge.props(f'color={self.get_login_status_class()}')

    def on_user_select(self, e):
        value = e.value
        if value and value in self.users_data:
            self.load_user_data(self.users_data[value])
            self._show_notification(f'已加载用户: {value}', 'positive')
            self.user_management_dialog.close()

    def load_user_data(self, data):
        self.start_city_input.value = data.get('start_city', '')
        self.end_city_input.value = data.get('end_city', '')

        self.update_stations('start')
        self.update_stations('end')

        start_station = data.get('start_station', '请选择')
        self.start_station_select.value = start_station if start_station in self.start_station_select.options else (self.start_station_select.options[0] if self.start_station_select.options else '请选择')

        end_station = data.get('end_station', '请选择')
        self.end_station_select.value = end_station if end_station in self.end_station_select.options else (self.end_station_select.options[0] if self.end_station_select.options else '请选择')

        self.train_date_input.value = data.get('train_date', '')
        self.train_list_input.value = ','.join(data.get('TRAIN_ID_LIST', []))

        self.name_input.value = data.get('NAME', '')
        self.gender_select.value = '男' if data.get('GENDER') == '0' else '女'
        self.id_input.value = data.get('ID', '')
        self.phone_input.value = data.get('PHONE_NUMBER', '')

        for name, code in PASSENGER_CLASS_CODES.items():
            if code == data.get('PASSENGER_CLASS', '1'):
                self.passenger_class_select.value = name
                break

        for name, code in TICKET_CLASS_CODES.items():
            if code == data.get('TICKET_CLASS', 'O'):
                self.ticket_class_select.value = name
                break

        self.filter_position_options()
        pos_code = data.get('choose_position', '')
        for name, code in POSITION_OPTIONS.items():
            if code == pos_code and name in self.position_select.options:
                self.position_select.value = name
                break

        self.start_time_input.value = data.get('start_time', '')

    def _refresh_user_dropdowns(self):
        options = list(self.users_data.keys()) if self.users_data else ['暂无配置']
        self.user_select.options = options
        self.user_select.update()

    def save_current_user(self):
        name = self.name_input.value
        if not name:
            self._show_notification('请输入姓名作为用户标识', 'warning')
            return
        self.users_data[name] = self.get_config_from_ui()
        self.save_users_data()
        self._refresh_user_dropdowns()
        self.user_select.value = name
        self._show_notification(f'配置 [{name}] 保存成功', 'positive')

    def delete_selected_user(self):
        name = self.user_select.value
        if name and name in self.users_data:
            del self.users_data[name]
            self.save_users_data()
            self._refresh_user_dropdowns()
            self.user_select.value = self.user_select.options[0] if self.user_select.options else None
            self._show_notification(f'配置 [{name}] 删除成功', 'positive')
        else:
            self._show_notification('请先选择要删除的用户', 'warning')

    def get_config_from_ui(self):
        train_list = [t.strip() for t in (self.train_list_input.value or '').split(',') if t.strip()]
        return {
            'start_city': self.start_city_input.value or '',
            'start_station': self.start_station_select.value or '',
            'end_city': self.end_city_input.value or '',
            'end_station': self.end_station_select.value or '',
            'train_date': self.train_date_input.value or '',
            'TRAIN_ID_LIST': train_list,
            'NAME': self.name_input.value or '',
            'GENDER': '0' if self.gender_select.value == '男' else '1',
            'ID': self.id_input.value or '',
            'PHONE_NUMBER': self.phone_input.value or '',
            'PASSENGER_CLASS': PASSENGER_CLASS_CODES.get(self.passenger_class_select.value, '1'),
            'TICKET_CLASS': TICKET_CLASS_CODES.get(self.ticket_class_select.value, 'O'),
            'choose_position': POSITION_OPTIONS.get(self.position_select.value, ''),
            'start_time': self.start_time_input.value or ''
        }

    def apply_config(self):
        self.config.load_from_dict(self.get_config_from_ui())

    def update_stations(self, station_type):
        if self.updating_stations: return
        self.updating_stations = True
        try:
            city = (self.start_city_input.value if station_type == 'start' else self.end_city_input.value).strip()
            select_obj = self.start_station_select if station_type == 'start' else self.end_station_select

            if not city or not self.config.CITYCODE:
                select_obj.options = ['请选择']
                select_obj.value = '请选择'
                select_obj.update()
                return

            matched = [s for s in self.config.CITYCODE.keys() if city in s or s in city]
            display_stations = matched[:15] if matched else ['请选择']
            select_obj.options = display_stations
            if select_obj.value not in display_stations:
                select_obj.value = display_stations[0] if display_stations else '请选择'

            select_obj.update()
        finally:
            self.updating_stations = False

    def on_station_change(self, station_type):
        if self.updating_city: return
        self.updating_city = True
        try:
            station = self.start_station_select.value if station_type == 'start' else self.end_station_select.value
            city_input = self.start_city_input if station_type == 'start' else self.end_city_input

            if station and station != '请选择':
                city = station
                for suffix in ['东', '西', '南', '北', '站', '机场', '火车站']:
                    if city.endswith(suffix):
                        city = city[:-len(suffix)]
                if city and city_input.value != city:
                    city_input.value = city
        finally:
            self.updating_city = False

    def set_current_time(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.start_time_input.value = current_time
        self._show_notification(f"已同步系统时间", "info")

    def filter_position_options(self, _e=None):
        berth_tickets = {"硬卧", "软卧", "动卧", "一等卧", "二等卧", "高级动卧", "高级软卧"}
        options = ["不限", "上铺", "中铺", "下铺"] if self.ticket_class_select.value in berth_tickets else ["不限", "A (靠窗)", "B (中间)", "C (过道)", "D (过道)", "F (靠窗)"]
        self.position_select.options = options
        if self.position_select.value not in options:
            self.position_select.value = "不限"
        self.position_select.update()

    def _update_qr_status(self, status_text, logged_in=False):
        self.qr_status_label.text = status_text
        if logged_in:
            self.logged_in = True
            self.update_login_status_display()
            ui.timer(1.5, self.qr_dialog.close, once=True)

    def poll_qr_status(self):
        if not self.qr_timer_active or not self.current_qr_uuid:
            return

        result = self.get_ticket.check_qr_code(self.current_qr_uuid)
        if result:
            result_code = str(result.get("result_code", ""))
            result_message = result.get("result_message", "")

            if result_message == "扫码登录成功" or result_code == '4':
                self._update_qr_status("正在获取验证令牌...")
                if self.get_ticket.get_login_token():
                    self._update_qr_status("登录成功！即将返回...", logged_in=True)
                    self._show_notification("账号登录成功", "positive")
                    self.qr_timer_active = False
                    self.qr_timer.deactivate()
            elif result_code == '1' or "请在手机上确认" in result_message:
                self._update_qr_status("等待手机端点击确认...")
            elif result_code == '0':
                self._update_qr_status("二维码有效，等待扫码...")

    def check_login_status(self):
        status = self.get_ticket.check_login_status()
        self.logged_in = bool(status)
        self.update_login_status_display()
        self._show_notification("检查完毕: 账号有效" if self.logged_in else "检查完毕: 会话已过期", "positive" if self.logged_in else "warning")

    def start_grab_task(self):
        if self.task_running:
            self._show_notification("已有任务在运行中，请勿重复点击", 'warning')
            return
        if not self.logged_in:
            self._show_notification("尚未登录 12306 账号，请先扫码", 'negative')
            self.get_qr_code()
            return

        self.apply_config()
        self.task_running = True
        self.task_status_label.text = "运行中"
        self.task_status_label.classes(replace='text-white bg-green-500')
        self.start_btn.props('loading')
        self._show_notification("引擎启动，开始执行策略", "positive")

        threading.Thread(target=self._run_grab, daemon=True).start()

    def _show_notification(self, message, notification_type='info'):
        self.pending_notifs.append((message, notification_type))

    def _run_grab(self):
        try:
            start_time_str = self.start_time_input.value
            if start_time_str:
                try:
                    target_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                    self.get_ticket._log(f"[SYS] 已设定目标开抢时间: {start_time_str}")
                    target_dt_advanced = target_dt - timedelta(seconds=self.config.advanced)

                    while self.task_running:
                        now = datetime.now()
                        diff = (target_dt - now).total_seconds()
                        diff_advanced = (target_dt_advanced - now).total_seconds()

                        if now >= target_dt_advanced:
                            self.get_ticket._log("[SYS] 倒计时结束，触发抢票逻辑！")
                            break

                        if diff > 0 and int(now.second) % 30 == 0:
                            self.logged_in = bool(self.get_ticket.check_login_status())
                            self.update_login_status_display()

                        if diff_advanced > 300: time.sleep(10)
                        elif diff_advanced > 60: time.sleep(1)
                        else: time.sleep(0.1)
                except Exception as e:
                    self.get_ticket._log(f"[ERR] 定时器解析失败，将立即执行: {e}")

            self.get_ticket._log("[SYS] 开始检索车次信息...")
            result = self.get_ticket.run()

            if result == 1:
                self.get_ticket._log("[SUCCESS] 恭喜！锁票成功！")
                self._show_notification("成功锁定席位！请火速前往 APP 支付", "positive")
            elif result == 2:
                self.get_ticket._log("[FAIL] 很遗憾，目标车票已售罄。")
                self._show_notification("车票已售罄，下次早点来哦", "warning")
            else:
                self.get_ticket._log("[END] 任务自动终止，未抢到票。")
                self._show_notification("任务结束，无可用车票", "info")
        except Exception as e:
            self.get_ticket._log(f"[ERR] 核心进程异常中止: {e}")
            self._show_notification(f"内部异常: {e}", "negative")
        finally:
            self.task_running = False
            self.task_status_label.text = "待命"
            self.task_status_label.classes(replace='text-gray-500 bg-gray-100')
            self.start_btn.props(remove='loading')

    def poll_logs(self):
        if not self.log_timer_active: return
        if self.get_ticket.logs:
            current_logs = self.get_ticket.logs
            if len(current_logs) > self.last_log_index:
                for entry in current_logs[self.last_log_index:]:
                    self.log_output.push(entry)
                self.last_log_index = len(current_logs)

        while getattr(self, 'pending_notifs', []):
            msg, n_type = self.pending_notifs.pop(0)
            ui.notify(msg, type=n_type, position='top')

    def clear_logs(self):
        self.get_ticket.logs = []
        self.log_output.clear()
        self.last_log_index = 0
        self.get_ticket._log("[SYS] 终端日志已清理")

    def create_qr_dialog(self):
        self.qr_dialog = ui.dialog()
        with self.qr_dialog:
            with ui.card().classes('p-8 shadow-2xl rounded-2xl flex flex-col items-center bg-white w-96'):
                ui.icon('qr_code', size='xl', color='indigo-700').classes('mb-2')
                ui.label('扫码安全登录').classes('text-2xl font-bold text-gray-800 mb-6')

                self.qr_image = ui.image('https://dummyimage.com/250x250/f3f4f6/a1a1aa.png&text=Loading...').classes('w-64 h-64 border-4 border-gray-100 rounded-xl mb-4')
                self.qr_status_label = ui.label('正在请求服务器...').classes('text-md text-indigo-600 font-medium text-center h-6')

                with ui.row().classes('gap-3 mt-6 w-full justify-center'):
                    ui.button('刷新二维码', icon='refresh', on_click=self.get_qr_code).props('outline color=primary')
                    ui.button('关闭', on_click=self.qr_dialog.close).props('flat color=grey')

    def create_user_management_dialog(self):
        self.user_management_dialog = ui.dialog()
        with self.user_management_dialog:
            with ui.card().classes('p-6 shadow-xl rounded-xl w-[400px] bg-white'):
                with ui.row().classes('items-center border-b pb-3 mb-4 w-full'):
                    ui.icon('manage_accounts', size='md', color='primary')
                    ui.label('高级账号配置管理').classes('text-xl font-bold ml-2')

                with ui.column().classes('gap-4 w-full'):
                    self.user_select = ui.select(
                        options=list(self.users_data.keys()) if self.users_data else ['暂无配置'],
                        label='选择历史配置',
                        on_change=self.on_user_select
                    ).classes('w-full').props('outlined dense')

                    with ui.row().classes('gap-2 w-full mt-2'):
                        ui.button('保存当前界面信息', icon='save', on_click=self.save_current_user).props('color=positive push').classes('flex-grow')
                        ui.button('删除所选', icon='delete', on_click=self.delete_selected_user).props('color=negative outline')

                ui.button('关闭面板', on_click=self.user_management_dialog.close).props('flat color=grey w-full mt-4')

    def show_user_management(self):
        self._refresh_user_dropdowns()
        self.user_management_dialog.open()

    def get_qr_code(self):
        self.qr_dialog.open()
        self.get_ticket.get_cookies()

        qr_uuid, qr_base64 = self.get_ticket.get_qr_code()

        if qr_uuid and qr_base64:
            self.qr_image.set_source(f"data:image/png;base64,{qr_base64}")
            self.qr_status_label.text = "请打开 12306 APP 扫一扫"
            self.current_qr_uuid = qr_uuid

            if hasattr(self, 'qr_timer'):
                self.qr_timer.deactivate()
            self.qr_timer_active = True
            self.qr_timer = ui.timer(2, self.poll_qr_status)
        else:
            self.qr_status_label.text = "获取失败，请点击刷新重试"
            self.qr_image.set_source('https://dummyimage.com/250x250/fce4e4/ef4444.png&text=Error')