import requests
import json
import time
import re
import os
from random import randint
from datetime import datetime
from urllib.parse import unquote


class GetTicket:
    # 通用浏览器headers（基于旧代码优化）
    BROWSER_HEADERS = {
        "Host": "kyfw.12306.cn",
        "Connection": "keep-alive",
        "sec-ch-ua-platform": "\"Windows\"",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "sec-ch-ua": "\"Microsoft Edge\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24\"",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "sec-ch-ua-mobile": "?0",
        "Origin": "https://kyfw.12306.cn",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
    }

    def __init__(self, config):
        self.config = config
        self.tickets = {}
        self._REPEAT_SUBMIT_TOKEN = ""
        self._key_check_isChange = ""
        self._allEncStr = ""
        self.ischoose_seat = False
        self.ischoose_beds = False
        self.noticket = False
        self.session = requests.Session()
        # 设置默认headers，模拟真实浏览器
        self.session.headers.update(self.BROWSER_HEADERS)
        self.sysbusy = "系统繁忙，请稍后重试！"
        self.logs = []

    def _log(self, msg):
        current_time = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{current_time}] {msg}"
        print(log_msg)
        self.logs.append(log_msg)

    def _logrecord(self, filename, data):
        # 仅当 logswitch 为 True 时记录日志到硬盘，方便调试查错
        if getattr(self.config, 'logswitch', False):
            os.makedirs("log", exist_ok=True)
            with open(f'log/{str(filename)}.txt', 'w', encoding='utf-8') as file:
                file.write(str(data))

    def _ischoose_seat(self, response, choose_type):
        if getattr(self.config, 'ischoose_position', False):
            data = response.get('data', {})
            can_seats = data.get('canChooseSeats', 'N')
            seats_choose = ["P", "9", "M", "O"]
            if choose_type in seats_choose:
                return can_seats == 'Y'
        return False

    def _ischoose_beds(self, response, choose_type):
        if getattr(self.config, 'ischoose_position', False):
            data = response.get('data', {})
            can_beds = data.get('canChooseBeds', 'N')
            beds_choose = ["3", "4", "F"]
            if choose_type in beds_choose:
                return can_beds == 'Y'
        return False

    @staticmethod
    def _choose_position_bed(choose_position):
        mapping = {'上铺': '001', '中铺': '010', '下铺': '100'}
        return mapping.get(choose_position, '000')

    def get_cookies(self):
        self._log("正在初始化 Cookie...")
        urls = [
            "https://kyfw.12306.cn/otn/login/conf",
            "https://kyfw.12306.cn/otn/index12306/getLoginBanner",
            "https://kyfw.12306.cn/passport/web/auth/uamtk-static"
        ]
        headers = self.BROWSER_HEADERS.copy()
        headers.update({"Accept": "*/*"})
        for url in urls:
            try:
                self.session.get(url, headers=headers, timeout=5)
            except Exception:
                pass

    def get_qr_code(self):
        url = "https://kyfw.12306.cn/passport/web/create-qr64"
        headers = self.BROWSER_HEADERS.copy()
        headers.update({
            "Accept": "*/*",
            "Referer": "https://kyfw.12306.cn/otn/leftTicket/init"
        })
        data = {"appid": "otn", "_json_att": ""}
        try:
            response = self.session.post(url, data=data, headers=headers, timeout=10)
            if response.status_code == 200:
                response_data = response.json()
                base64_image = response_data.get("image")
                uuid = response_data.get("uuid")
                if base64_image and uuid:
                    self._log("成功获取登录二维码")
                    return uuid, base64_image
        except Exception as e:
            self._log(f"获取二维码异常: {e}")
        return None, None

    def check_qr_code(self, uuid):
        url = "https://kyfw.12306.cn/passport/web/checkqr"
        headers = self.BROWSER_HEADERS.copy()
        headers.update({
            "Referer": "https://kyfw.12306.cn/otn/resources/login.html",
            "Origin": "https://kyfw.12306.cn"
        })
        data = {"uuid": uuid, 'appid': 'otn'}
        try:
            response = self.session.post(url, data=data, headers=headers, timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self._log(f"检查扫码状态异常: {e}")
        return None

    def get_login_token(self):
        self._log("正在获取验证令牌...")
        headers = self.BROWSER_HEADERS.copy()
        headers.update({
            "Referer": "https://kyfw.12306.cn/otn/resources/login.html",
            "Origin": "https://kyfw.12306.cn"
        })

        try:
            self.session.get("https://kyfw.12306.cn/login/userLogin", headers=headers)
            time.sleep(0.5)

            url = "https://kyfw.12306.cn/passport/web/auth/uamtk"
            response = self.session.post(url, data={'appid': 'otn'}, headers=headers, timeout=10)

            try:
                resp_json = response.json()
            except ValueError:
                self._log(f"第一步获取 uamtk 失败，状态码: {response.status_code}")
                return False

            if response.status_code == 200 and resp_json.get("result_message") == "验证通过":
                newapptk = resp_json.get("newapptk")
                self._log("第一步验证通过，获取 uamtk 成功")

                url_client = "https://kyfw.12306.cn/otn/uamauthclient"
                resp_client = self.session.post(url_client, data={'tk': newapptk}, headers=headers)

                try:
                    client_json = resp_client.json()
                except ValueError:
                    self._log("第二步 uamauthclient 解析响应失败。")
                    return False

                if resp_client.status_code == 200 and client_json.get("result_message") == "验证通过":
                    self._log("第二步验证通过，成功登录系统！")
                    return True
                else:
                    self._log(f"第二步验证失败: {client_json.get('result_message')}")
            else:
                self._log(f"第一步验证失败: {resp_json.get('result_message')}")
        except Exception as e:
            self._log(f"获取登录令牌遭遇网络异常: {e}")
        return False

    def check_login_status(self):
        url = "https://kyfw.12306.cn/otn/login/checkUser"
        headers = self.BROWSER_HEADERS.copy()
        headers.update({
            "Referer": "https://kyfw.12306.cn/otn/resources/login.html",
            "Origin": "https://kyfw.12306.cn"
        })
        data = {"appid": "otn", "_json_att": ""}
        try:
            response = self.session.post(url, data=data, headers=headers, timeout=5)
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if response_data.get('data', {}).get('flag'):
                        self._log("账号状态：存活")
                        return 1
                except ValueError:
                    pass
        except Exception:
            pass
        return 0

    def get_ticket_info(self):
        start_code = self.config.CITYCODE.get(self.config.start_station, "")
        end_code = self.config.CITYCODE.get(self.config.end_station, "")

        if not start_code or not end_code:
            self._log(f"内部错误：无法映射车站代码，出发地:{self.config.start_station}, 目的地:{self.config.end_station}")
            return 0

        url = f'https://kyfw.12306.cn/otn/leftTicket/query?leftTicketDTO.train_date={self.config.train_date}&leftTicketDTO.from_station={start_code}&leftTicketDTO.to_station={end_code}&purpose_codes=ADULT'
        headers = self.BROWSER_HEADERS.copy()
        headers.update({
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://kyfw.12306.cn/otn/leftTicket/init"
        })
        try:
            response = self.session.get(url, headers=headers, timeout=10)

            self._logrecord("get_tickets_url", url)

            try:
                data = response.json()
            except ValueError:
                self._logrecord("get_tickets_response_error", response.text)
                self._log("查票接口被拦截，请稍后再试。")
                return 0

            if data.get("data") is None:
                self._log("未获取到车票信息，可能是日期格式错误或暂未发售。")
                return 0

            train_info_list = data["data"]["result"]
            self.tickets.clear()
            for train_info in train_info_list:
                info = train_info.split("|")
                self.tickets[info[3]] = {
                    'all_trainname': info[2],
                    'from_station_name': info[6],
                    'to_station_name': info[7],
                    'start_time': info[8],
                    'arrive_time': info[9],
                    'seat_types': info[11],
                    'left_ticket': info[12],
                    'train_location': info[15],
                    'seat_discount_info': info[-3] if len(info) > 3 else '',
                    'secret_str': info[0]
                }
            self._logrecord("get_tickets_response", self.tickets)
            self._log(f"获取车票信息成功，共找到 {len(train_info_list)} 趟列车")
            return 1
        except Exception as e:
            self._log(f"获取车票异常: {e}")
            return 0

    @staticmethod
    def generate_uab_collina():
        return str(int(time.time() * 1000)) + ''.join([str(randint(0, 9)) for _ in range(11)])

    def create_order(self, train):
        url = "https://kyfw.12306.cn/otn/leftTicket/submitOrderRequest"
        headers = self.BROWSER_HEADERS.copy()
        data = {
            'secretStr': unquote(self.tickets[train]['secret_str']),
            'train_date': self.config.train_date,
            'back_train_date': '',
            'tour_flag': 'dc',
            'purpose_codes': '00',
            'query_from_station_name': self.config.start_city,
            'query_to_station_name': self.config.end_city,
            'bed_level_info': '',
            'seat_discount_info': self.tickets[train]['seat_discount_info'],
            'undefined': ''
        }

        start_code = self.config.CITYCODE.get(self.config.start_station, "")
        end_code = self.config.CITYCODE.get(self.config.end_station, "")

        try:
            self.session.cookies.set('_jc_save_fromStation',
                                     ''.join([f"%u{ord(c):04X}" for c in self.config.start_city + ","]) + start_code,
                                     domain='kyfw.12306.cn')
            self.session.cookies.set('_jc_save_toStation',
                                     ''.join([f"%u{ord(c):04X}" for c in self.config.end_city + ","]) + end_code,
                                     domain='kyfw.12306.cn')
            self.session.cookies.set('_jc_save_fromDate', self.config.train_date, domain='kyfw.12306.cn')
            self.session.cookies.set('_jc_save_toDate', str(datetime.today().date()), domain='kyfw.12306.cn')
            self.session.cookies.set('jc_save_wfdc_flag', 'dc', domain='kyfw.12306.cn')

            # 防风控环境伪装 Cookie
            self.session.cookies.set('guidesStatus', 'off', domain='kyfw.12306.cn')
            self.session.cookies.set('highContrastMode', 'defaltMode', domain='kyfw.12306.cn')
            self.session.cookies.set('ursorStatus', 'off', domain='kyfw.12306.cn')

            # 主动清理可能导致状态冲突的旧 Cookie
            for key in ['_passport_session', 'uamtk', 'BIGipServerportal']:
                if key in self.session.cookies:
                    del self.session.cookies[key]
        except Exception as e:
            self._log(f"写入/清理 Cookie 异常: {e}")

        self.session.cookies.set('_uab_collina', self.generate_uab_collina(), domain='kyfw.12306.cn')

        for times in range(getattr(self.config, 'grabfunction_max_try_times', 6)):
            response = self.session.post(url, data=data, headers=headers)

            self._logrecord("create_order_request_url", url)
            self._logrecord("create_order_request_data", data)
            self._logrecord("create_order_response_text", response.text)

            if response.status_code != 200:
                self._log(f"提交订单请求失败！状态码：{response.status_code}")
                continue
            if self.sysbusy in response.text:
                self._log("服务器繁忙 (创建订单)！")
                continue

            try:
                resp_json = response.json()
                if resp_json.get("status"):
                    self._log(f"[{train}] 创建订单请求通过！")
                    return True
            except ValueError:
                pass

        raise Exception("创建订单失败，超过最大重试次数")

    def init_order(self):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/initDc"
        headers = self.BROWSER_HEADERS.copy()
        headers.update({
            "Referer": "https://kyfw.12306.cn/otn/confirmPassenger/initDc"
        })
        data = {'_json_att': ''}
        self.session.cookies.update({'_uab_collina': self.generate_uab_collina()})

        for times in range(getattr(self.config, 'grabfunction_max_try_times', 6)):
            response = self.session.post(url, data=data, headers=headers)

            self._logrecord("init_order_url", url)
            self._logrecord("init_order_request_data", data)

            if response.status_code != 200 or self.sysbusy in response.text:
                continue
            try:
                self._REPEAT_SUBMIT_TOKEN = re.findall(r"var globalRepeatSubmitToken = '(.*?)'", response.text)[0]
                self._key_check_isChange = re.findall(r"'key_check_isChange':'(.*?)'", response.text)[0]
                self._log("订单初始化(initDc)提取 Token 成功！")
                return True
            except IndexError:
                self._log("提取 Token 数据失败！")
                continue
        raise Exception("订单初始化失败")

    def check_passengers(self):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs"
        headers = self.BROWSER_HEADERS.copy()
        data = {"_json_att": "", 'REPEAT_SUBMIT_TOKEN': self._REPEAT_SUBMIT_TOKEN}

        for times in range(getattr(self.config, 'grabfunction_max_try_times', 6)):
            response = self.session.post(url, data=data, headers=headers)

            self._logrecord("check_passengers_url", url)
            self._logrecord("check_passengers_request_data", data)
            self._logrecord("check_passengers_response_text", response.text)

            if response.status_code != 200 or self.sysbusy in response.text:
                continue
            try:
                # 获取 12306 账号绑定的所有乘车人列表
                passengers = response.json()['data']['normal_passengers']
                target_name = getattr(self.config, 'NAME', '').strip()

                # 遍历查找与 UI 输入姓名匹配的乘车人
                matched_passenger = None
                for passenger in passengers:
                    if passenger.get('passenger_name') == target_name:
                        matched_passenger = passenger
                        break

                # 如果找到了匹配的人，提取他的加密凭证
                if matched_passenger:
                    self._allEncStr = matched_passenger['allEncStr']
                    self._log(f"乘车人映射成功！已锁定: {target_name}")
                    return True
                else:
                    self._log(f"【阻断错误】12306 账号中未找到名为 '{target_name}' 的乘车人！请核对是否已在官方添加此人。")
                    # 找不到人直接返回 False 阻断，防止乱买票
                    return False

            except (ValueError, KeyError, IndexError):
                continue

        raise Exception("乘车人信息查询失败，请检查12306账号中是否有乘车人或网络是否通畅")

    def check_order_info(self):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/checkOrderInfo"
        headers = self.BROWSER_HEADERS.copy()
        passenger_str = f"{self.config.TICKET_CLASS},{self.config.GENDER},{self.config.PASSENGER_CLASS},{self.config.NAME},1,{self.config.ID},{self.config.PHONE_NUMBER},N,{self._allEncStr}"
        old_passenger_str = f"{self.config.NAME},1,{self.config.ID},{self.config.PASSENGER_CLASS}_"

        data = {
            "cancel_flag": "2",
            "bed_level_order_num": "000000000000000000000000000000",
            "passengerTicketStr": passenger_str,
            "oldPassengerStr": old_passenger_str,
            "tour_flag": "dc",
            "whatsSelect": "1",
            "scene": "nc_login",
            "_json_att": "",
            "REPEAT_SUBMIT_TOKEN": self._REPEAT_SUBMIT_TOKEN,
        }
        self.session.cookies.update({'_uab_collina': self.generate_uab_collina()})
        self.noticket = False

        for times in range(getattr(self.config, 'grabfunction_max_try_times', 6)):
            response = self.session.post(url, data=data, headers=headers)

            self._logrecord("check_order_info_url", url)
            self._logrecord("check_order_info_request_data", data)
            self._logrecord("check_order_info_response_text", response.text)

            if response.status_code != 200 or self.sysbusy in response.text:
                continue
            if "仅剩0" in response.text:
                self._log("警告：系统校验当前余票为 0！")
                self.noticket = True
                return False

            try:
                resp_json = response.json()
                if resp_json.get("status"):
                    self.ischoose_seat = self._ischoose_seat(resp_json, self.config.TICKET_CLASS)
                    self.ischoose_beds = self._ischoose_beds(resp_json, self.config.TICKET_CLASS)
                    self._log("校验订单信息成功！")
                    return True
            except ValueError:
                pass
        raise Exception("校验订单信息失败")

    def submit_order(self, train):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/getQueueCount"
        headers = self.BROWSER_HEADERS.copy()
        date_obj = datetime.strptime(self.config.train_date, "%Y-%m-%d")
        train_date_formatted = f"{date_obj.strftime('%a')} {self.config.month_dict[date_obj.month]} {date_obj.strftime('%d')} {date_obj.year} 00:00:00 GMT+0800 (中国标准时间)"

        data = {
            "train_date": train_date_formatted,
            "train_no": self.tickets[train]["all_trainname"],
            "stationTrainCode": train,
            "seatType": self.config.TICKET_CLASS,
            "fromStationTelecode": self.config.CITYCODE.get(self.config.start_station, ""),
            "toStationTelecode": self.config.CITYCODE.get(self.config.end_station, ""),
            "leftTicket": self.tickets[train]["left_ticket"],
            "purpose_codes": "00",
            "train_location": self.tickets[train]['train_location'],
            "_json_att": "",
            "REPEAT_SUBMIT_TOKEN": self._REPEAT_SUBMIT_TOKEN
        }
        self.session.cookies.update({'_uab_collina': self.generate_uab_collina()})

        for times in range(getattr(self.config, 'grabfunction_max_try_times', 6)):
            response = self.session.post(url, data=data, headers=headers)

            self._logrecord("submit_order_url", url)
            self._logrecord("submit_order_request_data", data)
            self._logrecord("submit_order_response_text", response.text)

            if response.status_code != 200 or self.sysbusy in response.text:
                continue
            self._log("请求进队确认成功 (getQueueCount)！")
            return True
        raise Exception("进队列请求失败")

    def confirm_order(self, train):
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/confirmSingleForQueue'
        headers = self.BROWSER_HEADERS.copy()
        passenger_str = f"{self.config.TICKET_CLASS},{self.config.GENDER},{self.config.PASSENGER_CLASS},{self.config.NAME},1,{self.config.ID},{self.config.PHONE_NUMBER},N,{self._allEncStr}"
        old_passenger_str = f"{self.config.NAME},1,{self.config.ID},{self.config.PASSENGER_CLASS}_"

        data = {
            'passengerTicketStr': passenger_str,
            'oldPassengerStr': old_passenger_str,
            'purpose_codes': '00',
            'key_check_isChange': self._key_check_isChange,
            'leftTicketStr': self.tickets[train]["left_ticket"],
            'train_location': self.tickets[train]['train_location'],
            'choose_seats': getattr(self.config, 'choose_position', '') if self.ischoose_seat else '',
            'seatDetailType': self._choose_position_bed(
                getattr(self.config, 'choose_position', '')) if self.ischoose_beds else '000',
            'is_jy': 'N',
            'is_cj': 'N' if self.config.PASSENGER_CLASS == "1" else 'Y',
            'encryptedData': '',
            'whatsSelect': '1',
            'roomType': '00',
            'dwAll': 'N',
            '_json_att': '',
            'REPEAT_SUBMIT_TOKEN': self._REPEAT_SUBMIT_TOKEN
        }
        self.session.cookies.update({'_uab_collina': self.generate_uab_collina()})

        for times in range(getattr(self.config, 'grabfunction_max_try_times', 6)):
            response = self.session.post(url, data=data, headers=headers)

            self._logrecord("confirm_order_url", url)
            self._logrecord("confirm_order_request_data", data)
            self._logrecord("confirm_order_response_text", response.text)

            if response.status_code != 200 or self.sysbusy in response.text:
                continue
            try:
                if response.json().get('data', {}).get('submitStatus'):
                    self._log("最终排队指令投递成功！")
                    return True
            except ValueError:
                pass
        raise Exception("确认订单失败")

    def base_log(self):
        url = "https://kyfw.12306.cn/otn/basedata/log"
        headers = self.BROWSER_HEADERS.copy()
        data = {
            'type': 'dc',
            '_json_att': "",
            'REPEAT_SUBMIT_TOKEN': self._REPEAT_SUBMIT_TOKEN
        }

        if '_uab_collina' in self.session.cookies:
            del self.session.cookies['_uab_collina']

        for times in range(getattr(self.config, 'grabfunction_max_try_times', 6)):
            response = self.session.post(url, data=data, headers=headers)

            self._logrecord("base_log_url", url)
            self._logrecord("base_log_request_data", data)
            self._logrecord("base_log_response_text", response.text)

            if response.status_code != 200 or self.sysbusy in response.text:
                continue
            self._log("记录日志成功 (base_log)！")
            return True
        return False

    def queue_order(self):
        random_ts = str(int(time.time() * 1000))
        url = f"https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime?random={random_ts}&tourFlag=dc&_json_att=&REPEAT_SUBMIT_TOKEN={self._REPEAT_SUBMIT_TOKEN}"
        headers = self.BROWSER_HEADERS.copy()
        headers.update({
            "Accept": "application/json, text/javascript, */*; q=0.01"
        })

        for times in range(getattr(self.config, 'grabfunction_max_try_times', 6) * 3):
            response = self.session.get(url, headers=headers)

            self._logrecord("queue_order_url", url)
            self._logrecord("queue_order_response_text", response.text)

            if response.status_code != 200 or self.sysbusy in response.text:
                time.sleep(1)  # 遇错稍微缓一下
                continue
            try:
                resp_data = response.json().get('data', {})
                order_id = resp_data.get('orderId')
                wait_time = resp_data.get('waitTime', 0)

                if order_id:
                    self._log(f"出票成功！订单号: {order_id}，请前往 12306 客户端/网页版完成支付！")
                    return True

                self._log(f"排队中... 预计等待时间: {wait_time} 秒")
                if wait_time == -2:
                    self._log("出票失败 (排队被拒或无票)")
                    return False

                if wait_time == 4 or wait_time == -100:
                    time.sleep(15)
                    continue

            except ValueError:
                pass

            time.sleep(3)
        return False

    def run(self):
        while True:
            if self.get_ticket_info():
                break
            time.sleep(1)

        try_time = 0
        max_tries = getattr(self.config, 'max_try_times', 3)
        while try_time < max_tries:
            try_time += 1
            self._log(f"=== 开始第 {try_time} 轮抢票尝试 ===")
            for train in getattr(self.config, 'TRAIN_ID_LIST', []):
                if not train or train not in self.tickets:
                    self._log(f"跳过未配置或不在售列表的车次: {train}")
                    continue
                try:
                    self._log(f"锁定车次 {train}，执行链路请求...")
                    self.create_order(train)
                    self.init_order()
                    if not self.check_passengers():
                        continue
                    if not self.check_order_info():
                        if self.noticket:
                            continue
                    self.submit_order(train)
                    self.confirm_order(train)
                    self.base_log()  # 执行基于数据的防封锁日志记录
                    if self.queue_order():
                        return 1
                except Exception as e:
                    self._log(f"本链路断开: {str(e)}")
            if self.noticket:
                self._log("本轮所有指定车票已被抢完！")
                return 2
        return 0