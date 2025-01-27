import tkinter as tk
from tkinter import ttk
from datetime import datetime
from tkcalendar import DateEntry  # 导入tkcalendar中的DateEntry
import Getticket
import user
import time
import ntplib
import json
import threading
import numpy as np

# 实例化 GetTicket 类
web = Getticket.GetTicket()

# 定义保存文件路径
USER_DATA_FILE = "data/user_data.json"

class TicketUI:
    def __init__(self, root):
        self.root = root
        self.root.title("12306 抢票助手")
        self.root.geometry("800x700")
        self.ntpserver = user.ntpserver

        #数据初始化
        self.user_frame = None
        self.scrollbar = None
        self.log_text = None
        self.log_frame = None
        self.start_button = None
        self.login_button = None
        self.target_time_entry = None
        self.target_time_label = None
        self.train_id_entry = None
        self.date_entry = None
        self.end_station_entry = None
        self.end_city_entry = None
        self.start_station_entry = None
        self.start_city_entry = None
        self.trip_frame = None
        self.seat_position = None
        self.seat_class = None
        self.phone_entry = None
        self.id_entry = None
        self.gender_entry = None
        self.name_entry = None

        # 定义座位类别和限制条件
        self.seat_options = {
            "特等座": ["A", "C", "F"],
            "商务座": ["A", "C", "F"],
            "一等座": ["A", "C", "D", "F"],
            "二等座": ["A", "B", "C", "D", "F"],
            "高级动卧": [""],
            "高级软卧": [""],
            "一等卧": [""],
            "动卧": [""],
            "二等卧": [""],
            "硬座": [""],
            "软座": [""],
            "硬卧": [""],
            "软卧": [""]
        }
        self.seat_position_codes ={
            "特等座": "P",
            "商务座": "9",
            "一等座": "M",
            "二等座": "O",
            "高级动卧": "A",
            "高级软卧": "6",
            "一等卧": "I",
            "动卧": "F",
            "二等卧": "J",
            "硬座": "1",
            "软座": "2",
            "硬卧": "3",
            "软卧": "4"
        }
        # 初始化UI
        self._setup_ui()

        # 加载用户数据
        self._load_user_data()

    def _setup_ui(self):
        # 日志框
        self.log_frame = tk.Frame(self.root)
        self.log_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(self.log_frame, wrap=tk.WORD, height=10, font=("楷体", 10))
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar = tk.Scrollbar(self.log_frame, command=self.log_text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text['yscrollcommand'] = self.scrollbar.set
        self._log("程序启动成功！")

        # 用户信息设置
        self.user_frame = tk.LabelFrame(self.root, text="用户信息", font=("楷体", 12))
        self.user_frame.pack(pady=10, fill=tk.X)

        tk.Label(self.user_frame, text="姓名:", font=("楷体", 12)).grid(row=0, column=0, padx=5)
        self.name_entry = tk.Entry(self.user_frame, width=20, font=("楷体", 12))
        self.name_entry.grid(row=0, column=1, padx=5)

        tk.Label(self.user_frame, text="性别 (0 男, 1 女):", font=("楷体", 12)).grid(row=0, column=2, padx=5)
        self.gender_entry = tk.Entry(self.user_frame, width=10, font=("楷体", 12))
        self.gender_entry.grid(row=0, column=3, padx=5)

        tk.Label(self.user_frame, text="身份证号:", font=("楷体", 12)).grid(row=1, column=0, padx=5)
        self.id_entry = tk.Entry(self.user_frame, width=25, font=("楷体", 12))
        self.id_entry.grid(row=1, column=1, padx=5)

        tk.Label(self.user_frame, text="手机号:", font=("楷体", 12)).grid(row=1, column=2, padx=5)
        self.phone_entry = tk.Entry(self.user_frame, width=15, font=("楷体", 12))
        self.phone_entry.grid(row=1, column=3, padx=5)

        # 座位等级和位置选择
        tk.Label(self.user_frame, text="座位等级:", font=("楷体", 12)).grid(row=2, column=0, padx=5)
        self.seat_class = ttk.Combobox(self.user_frame, font=("楷体", 12), state="readonly")
        self.seat_class['values'] = list(self.seat_options.keys())
        self.seat_class.grid(row=2, column=1, padx=5)
        self.seat_class.bind("<<ComboboxSelected>>", self._update_seat_positions)

        tk.Label(self.user_frame, text="座位位置:", font=("楷体", 12)).grid(row=2, column=2, padx=5)
        self.seat_position = ttk.Combobox(self.user_frame, font=("楷体", 12), state="readonly")
        self.seat_position.grid(row=2, column=3, padx=5)

        # 行程信息设置
        self.trip_frame = tk.LabelFrame(self.root, text="行程信息", font=("楷体", 12))
        self.trip_frame.pack(pady=10, fill=tk.X)

        tk.Label(self.trip_frame, text="出发城市:", font=("楷体", 12)).grid(row=0, column=0, padx=5)
        self.start_city_entry = tk.Entry(self.trip_frame, width=20, font=("楷体", 12))
        self.start_city_entry.grid(row=0, column=1, padx=5)

        tk.Label(self.trip_frame, text="出发车站:", font=("楷体", 12)).grid(row=0, column=2, padx=5)
        self.start_station_entry = ttk.Combobox(self.trip_frame, width=20, font=("楷体", 12))
        self.start_station_entry.grid(row=0, column=3, padx=5)
        self.start_station_entry.bind('<KeyRelease>', self._update_start_combobox)

        tk.Label(self.trip_frame, text="目的城市:", font=("楷体", 12)).grid(row=1, column=0, padx=5)
        self.end_city_entry = tk.Entry(self.trip_frame, width=20, font=("楷体", 12))
        self.end_city_entry.grid(row=1, column=1, padx=5)

        tk.Label(self.trip_frame, text="目的车站:", font=("楷体", 12)).grid(row=1, column=2, padx=5)
        self.end_station_entry = ttk.Combobox(self.trip_frame, width=20, font=("楷体", 12))
        self.end_station_entry.grid(row=1, column=3, padx=5)
        self.end_station_entry.bind('<KeyRelease>', self._update_end_combobox)

        tk.Label(self.trip_frame, text="乘车日期(YYYY-MM-DD):", font=("楷体", 12)).grid(row=2, column=0, padx=5)
        self.date_entry = DateEntry(self.trip_frame, width=18, font=("楷体", 12), date_pattern='yyyy-mm-dd')
        self.date_entry.grid(row=2, column=1, padx=5)

        tk.Label(self.trip_frame, text="车次列表 (逗号分隔):", font=("楷体", 12)).grid(row=2, column=2, padx=5)
        self.train_id_entry = tk.Entry(self.trip_frame, width=25, font=("楷体", 12))
        self.train_id_entry.grid(row=2, column=3, padx=5)

        # 抢票时间设置
        self.target_time_label = tk.Label(self.root, text="设置抢票时间 (格式: YYYY-MM-DD HH:MM:SS):", font=("楷体", 12))
        self.target_time_label.pack(pady=5)
        self.target_time_entry = tk.Entry(self.root, width=30, font=("楷体", 12))
        self.target_time_entry.pack(pady=5)
        # 操作按钮
        self.login_button = tk.Button(self.root, text="登录", font=("楷体", 12), command=self._start_login_thread)
        self.login_button.pack(pady=5)

        self.start_button = tk.Button(self.root, text="开始抢票", font=("楷体", 12), command=self._start_ticket_grab_thread)
        self.start_button.pack(pady=5)

    # 更新Combobox的内容
    def _update_start_combobox(self, event):
        query = self.start_station_entry.get().lower()  # 获取输入并转为小写
        matched_items = []

        # 根据输入的内容匹配字典的键
        if query:
            for key in web.user.CITYCODE.keys():
                if query in key.lower():  # 如果字典键包含输入字符
                    matched_items.append(key)
        # 更新Combobox的内容，只显示前5项匹配
        self.start_station_entry['values'] = matched_items[:5]
        current_text = self.start_station_entry.get()
        if current_text not in matched_items:
            self.start_station_entry.set(current_text)  # 保持原本输入的文本

    def _update_end_combobox(self, event):
        query = self.end_station_entry.get().lower()  # 获取输入并转为小写
        matched_items = []
        # 根据输入的内容匹配字典的键
        if query:
            for key in web.user.CITYCODE.keys():
                if query in key.lower():  # 如果字典键包含输入字符
                    matched_items.append(key)
        # 更新Combobox的内容，只显示前5项匹配
        self.end_station_entry['values'] = matched_items[:5]
        current_text = self.end_station_entry.get()
        if current_text not in matched_items:
            self.end_station_entry.set(current_text)  # 保持原本输入的文本

    def _log(self, message):
        """记录日志信息并实时更新界面"""
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{time_str}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update()  # 强制刷新界面

    def _update_seat_positions(self, event):
        """根据座位等级更新可选位置"""
        selected_class = self.seat_class.get()
        positions = self.seat_options.get(selected_class, ["不可选"])
        self.seat_position['values'] = positions
        self.seat_position.current(0)

    def _start_login_thread(self):
        """启动登录线程"""
        thread = threading.Thread(target=self._login)
        thread.daemon = True  # 设置为守护线程
        thread.start()

    def _login(self):
        """执行登录"""
        try:
            self._save_user_data()
            web.get_cookies()
            self._log("请扫描二维码登录...")
            web.login()
            result = web.check_login_status()
            if result:
                self._log("登录成功！")
            else:
                self._log("登录失败，请重试！")

        except Exception as e:
            self._log(f"登录失败: {str(e)}")

    def _start_ticket_grab_thread(self):
        """启动抢票线程"""
        thread = threading.Thread(target=self._start_ticket_grab)
        thread.daemon = True  # 设置为守护线程
        thread.start()

    def _start_ticket_grab(self):
        """开始抢票"""
        try:
            # 更新用户信息
            web.user.NAME = self.name_entry.get().strip()
            web.user.GENDER = self.gender_entry.get().strip()
            web.user.ID = self.id_entry.get().strip()
            web.user.PHONE_NUMBER = self.phone_entry.get().strip()
            web.user.TICKET_CLASS = self.seat_position_codes[self.seat_class.get()]
            web.user.choose_seats = self.seat_position.get()
            web.user.start_city = self.start_city_entry.get().strip()
            web.user.start_station = self.start_station_entry.get().strip()
            web.user.end_city = self.end_city_entry.get().strip()
            web.user.end_station = self.end_station_entry.get().strip()
            web.user.train_date = self.date_entry.get().strip()
            web.user.TRAIN_ID_LIST = self.train_id_entry.get().strip().split(',')
            self._save_user_data()#保存用户信息

            #输出用户信息
            self._log(f"用户: {web.user.NAME}, "
                      f"车次: {web.user.TRAIN_ID_LIST},"
                      f" 座位等级: {web.user.TICKET_CLASS},"
                      f"上车站:{web.user.start_station},"
                      f"下车站:{web.user.end_station},"
                      f"出发时间:{web.user.train_date}")

            # 初始化创建 ntplib 客户端对象,并对比本地时间
            client = ntplib.NTPClient()
            self._log(f"当前使用ntp服务器为：{self.ntpserver}")
            try:
                dt = datetime.fromtimestamp(int(client.request(self.ntpserver).tx_time))
                self._log(f"当前NTP时间: {dt}")
                self._log(f"当前本地时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception as e:
                self._log(f"获取NTP时间失败: {e}")
                self._log("建议检查NTP服务器地址！")
                self._log(f"当前本地时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # 首次检查登录状态
            self._log(f"正在检查登录状态...")
            result = web.check_login_status()
            if result:
                self._log(f"登陆状态正常")
            else:
                self._log(f"登录状态异常，请重新登录！")
                return 0

            # 验证时间格式
            target_time_str = self.target_time_entry.get().strip()
            target_time = datetime.strptime(target_time_str, "%Y-%m-%d %H:%M:%S")  # 将str转化为UTC标准时间格式
            target_time_unix = time.mktime(target_time.timetuple())  # 将UTC转化为unix时间戳
            pattern =""#初始化抢票时间模式
            self._log(f"抢票设置时间为: {target_time_str}")
            self._log("等待抢票时间到达...")
            # 首先使用本地时间，直到开票前一分钟
            before_now_local=datetime.now()
            while True:
                now_local = datetime.now()
                # 每两分钟检查一次登录状态
                if (now_local.minute % 2) == 0 and now_local.minute != before_now_local.minute:
                    self._log(f"正在检查登录状态...")
                    result = web.check_login_status()
                    if result:
                        before_now_local = now_local
                        self._log(f"当前时间: {now_local.strftime('%Y-%m-%d %H:%M:%S')}")
                        self._log(f"登陆状态正常")
                    else:
                        self._log(f"登录状态异常，请重新登录！")
                        break  # 登录失败退出循环
                if (target_time-now_local).total_seconds() <= 60 :
                    self._log("距离开票不足一分钟！尝试切换为NTP授时模式！")
                    try:
                        ntp = client.request(self.ntpserver).tx_time  # 测试ntp服务器响应，返回值精度可达小数后七位
                        pattern = "ntp"
                        break
                    except Exception as e:
                        self._log(f"获取NTP时间失败: {e}")
                        pattern = "local"
                        break

            #切入本地时间模式
            if pattern == "local":
                self._log("切换为本地时间模式！")
                while True:
                    if datetime.now()>= target_time:
                        # 执行抢票程序
                        self._log("抢票时间到达，开始抢票...")
                        result = web.run()
                        if result:
                            self._log("抢票成功！请10分钟内到在 12306 支付订单。")
                            break
                        else:
                            self._log("抢票失败，请重试！")
                            break  # 执行完退出循环

            # 切入NTP授时模式
            if pattern == "ntp":
                self._log("成功切换为NTP授时模式！正在进行NTP时间校准！")
                #与NTP授时校准
                adjust_times = 0
                all_star_time = []
                while adjust_times<user.adjust_times_max:
                    try:
                        #获取ntp时间戳，与目标时间戳作差，最后加上time.perf_counter的当前数值，得到启动抢票时的time.perf_counter数值
                        npt_time = client.request(self.ntpserver).tx_time
                        star_time=float(time.perf_counter())+(float(target_time_unix)-float(npt_time))
                        all_star_time.append(star_time)
                        adjust_times += 1
                    except Exception as e:
                        print(f"NTP请求失败: {str(e)}")
                #使用IQR（四分位数间距）来去除离群值,避免网络波动导致误差
                Q1 = np.percentile(all_star_time, 25)
                Q3 = np.percentile(all_star_time, 75)
                IQR = Q3 - Q1
                # 定义离群值的阈值（1.5倍 IQR）
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                # 去除离群值
                filtered_all_star_time = [x for x in all_star_time if lower_bound <= x <= upper_bound]
                # 计算过滤后的数据的平均值
                filtered_star_time = np.mean(filtered_all_star_time)
                self._log("已完成时间校准！")
                self._log("注意:以下时间戳为本系统时间戳，并非NTP授时时间戳")
                self._log(f"当前时间戳为:{time.perf_counter()}")
                self._log(f"目标时间戳为：{filtered_star_time}")

                while True:
                    # 判断当前时间是否到达目标时间,并不再进行登录检查
                    if time.perf_counter() >= (float(filtered_star_time)-user.advanced):
                        # 执行抢票程序
                        self._log("抢票时间到达，开始抢票...")
                        result = web.run()
                        if result:
                            self._log("抢票成功！请10分钟内到在 12306 支付订单。")
                            break
                        else:
                            self._log("抢票失败，请重试！")
                            break  # 执行完退出循环

        except ValueError:
            self._log("数据格式错误，请检查输入格式！")
        except ConnectionError:
            self._log("网络异常，请检查网络连接！")
        except Exception as e:
            self._log(f"抢票失败: {str(e)}")

    def _save_user_data(self):
        """保存用户输入数据到文件"""
        data = {
            "name": self.name_entry.get().strip(),
            "gender": self.gender_entry.get().strip(),
            "id": self.id_entry.get().strip(),
            "phone": self.phone_entry.get().strip(),
            "seat_class": self.seat_class.get(),
            "seat_position": self.seat_position.get(),
            "start_city": self.start_city_entry.get().strip(),
            "start_station": self.start_station_entry.get().strip(),
            "end_city": self.end_city_entry.get().strip(),
            "end_station": self.end_station_entry.get().strip(),
            # "train_date": self.date_entry.get().strip(),
            "train_id_list": self.train_id_entry.get().strip(),
            "target_time": self.target_time_entry.get().strip()
        }
        with open(USER_DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        self._log("用户数据已保存！")

    def _load_user_data(self):
        """从文件加载用户数据"""
        try:
            with open(USER_DATA_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
                self.name_entry.insert(0, data.get("name", ""))
                self.gender_entry.insert(0, data.get("gender", ""))
                self.id_entry.insert(0, data.get("id", ""))
                self.phone_entry.insert(0, data.get("phone", ""))
                self.seat_class.set(data.get("seat_class", ""))
                self.seat_position.set(data.get("seat_position", ""))
                self.start_city_entry.insert(0, data.get("start_city", ""))
                self.start_station_entry.insert(0, data.get("start_station", ""))
                self.end_city_entry.insert(0, data.get("end_city", ""))
                self.end_station_entry.insert(0, data.get("end_station", ""))
                # self.date_entry.insert(0, data.get("train_date", ""))
                self.train_id_entry.insert(0, data.get("train_id_list", ""))
                self.target_time_entry.insert(0, data.get("target_time", ""))
                self._log("用户数据已加载！")
        except FileNotFoundError:
            self._log("未找到用户数据文件，使用默认设置")
        except json.JSONDecodeError:
            self._log("用户数据文件格式错误，请检查！")


if __name__ == "__main__":
    Root = tk.Tk()
    TicketUI(Root)
    Root.mainloop()
