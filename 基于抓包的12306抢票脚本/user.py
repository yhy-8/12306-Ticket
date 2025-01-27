import urllib.request as r

#用户可以自定义的参数
ntpserver = 'ntp.aliyun.com' #ntp服务器网址
max_try_time=5   #抢票尝试次数
logswitch=False   #是否开始日志记录(True或者False)，开启后会降低抢票速度，建议正常使用不开启
advanced=0.0     #提前发送请求时间，单位(s)。适当的提前可以规避网络延迟，提前过多会导致多次请求失败，达到五次会断开连接！仅NTP模式可用
adjust_times_max=80  #ntp授时校准，取平均


# 由于火车站使用三字码，所以我们需要先获取站点对应的三字码
code_url = r"https://kyfw.12306.cn/otn/resources/js/framework/station_name.js"
Code_Data = r.urlopen(code_url).read().decode('utf-8')


# 处理获得的字符串，返回字典类型
def zip_dic(code_data):
    code_data = code_data[20:]
    list_code = code_data.split("|")
    a = 1
    b = 2
    t1 = []
    t2 = []
    while  a < len(list_code):
        t1.append(list_code[a])
        t2.append(list_code[b])
        a = a + 5
        b = b + 5
    dic = dict(zip(t1, t2))
    return dic


CITYCODE =  zip_dic(Code_Data)

month_dict = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Srp",
    10: "Oct",
    11: "Nov",
    12: "Dec"
    }

# 开始抢票时间，格式为"2025-01-04 08:00:00"
start_time = ""

# 火车的发车日期，格式为"2025-01-04"
train_date = ""
'''
# 特等座 P 选座只有A、C、F
# 商务座 9 选座只有A、C、F
# 一等座 M 选座为A、C、D、F
# 二等座 O 选座为A、B、C、D、F（不是0，是大写的字母偶）
# 高级动卧 A 不能选铺位
# 高级软卧 6 不能选铺位
# 一等卧 I 不能选铺位
# 动卧 F 下铺 上铺
# 二等卧 J 不能选铺位？
# 硬座 1 不能选座
# 软座 2 不能选座
# 硬卧 3 下铺 中铺 上铺
# 软卧 4 下铺 上铺
'''
TICKET_CLASS = ""
# 选择的座位位置有A,B,C,D,E,F
choose_seats = ''
# 性别，0 通常代表男，1 代表女。
GENDER = ""
# 乘客的名字
NAME = ""
'''
1: 乘客的身份类型（1
代表成人）。
1 | 成人票 |
2 | 儿童票 |
3 | 学生票 |
4 | 残军票 |
'''
PASSENGER_CLASS = ""
# 乘客的身份证号码
ID = ""
# 乘客的手机号
PHONE_NUMBER = ""
# 要订的车次
TRAIN_ID_LIST = ['']
# 出发城市
start_city = ""
# 出发车站
start_station = ""
# 目的城市
end_city = ""
# 目的车站
end_station = ""
