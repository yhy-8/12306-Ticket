import time
import sys
import threading
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class Qiangpiao():
    def __init__(self,from_station,to_station,depart_time,train_num,passenger):
        self.login_url = 'https://kyfw.12306.cn/otn/resources/login.html'
        self.init_my_url = 'https://kyfw.12306.cn/otn/view/index.html'
        self.order_url = 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'
        #input("出发地：")
        self.from_station = from_station
        # input("目的地：")
        self.to_station = to_station

        # 出发时间(格式必须是Y-M-D的方式，并且M和D必须要两位，比如02)
        self.depart_time = depart_time

        # 列车号
        self.train_num = train_num
        self.passenger = passenger

        self.driver = webdriver.Edge()

        self.spinner=Spinner()#实例化等待动画类



    def _login(self):
        self.driver.get(self.login_url)
        # 窗口最大化
        self.driver.maximize_window()
        try:
            #跳转扫码登录界面
            self.driver.find_element(By.XPATH,'//*[@class="login-box"]/ul/li[2]/a').click()
            WebDriverWait(self.driver,120).until(EC.url_to_be(self.init_my_url))#等待登录，超过120s认为超时
            print("登录成功！")
        except TimeoutException:
            print("登录超时!(120s)")


    def _enter_order_ticket(self):
        try:
            action = ActionChains(self.driver)  # 实例化一个动作链对象
            #等待网页加载
            element = WebDriverWait(self.driver, 30).until(
                EC.visibility_of_element_located((By.LINK_TEXT, '车票'))
            )
            action.move_to_element(element).perform()
            single_ticket_element = WebDriverWait(self.driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="J-chepiao"]/div/div/ul/li/a'))
            )
            single_ticket_element.click()
        except TimeoutException:
            print("元素加载超时!(30s)")


    def _search_ticket(self):
        try:
            #出发地输入
            self.driver.find_element(By.ID,"fromStationText").click()
            self.driver.find_element(By.ID,"fromStationText").send_keys(self.from_station)
            self.driver.find_element(By.ID,"fromStationText").send_keys(Keys.ENTER)
            #目的地输入
            self.driver.find_element(By.ID,"toStationText").click()
            self.driver.find_element(By.ID,"toStationText").send_keys(self.to_station)
            self.driver.find_element(By.ID,"toStationText").send_keys(Keys.ENTER)
            #出发日期输入
            self.driver.find_element(By.ID,"train_date").click()
            self.driver.find_element(By.ID, "train_date").clear()#不删除原有的日期会导致叠加
            self.driver.find_element(By.ID, "train_date").send_keys(self.depart_time)
            self.driver.find_element(By.ID, "train_date").send_keys(Keys.ENTER)

            # 等待查询按钮是否可用
            WebDriverWait(self.driver, 30).until(EC.element_to_be_clickable((By.ID, "query_ticket")))
            #执行点击事件
            search_btn = self.driver.find_element(By.ID,"query_ticket")
            search_btn.click()
        except TimeoutException:
            print("元素加载超时！(120s)")
        try:
            #等待查票信息加载
            WebDriverWait(self.driver, 120).until(EC.presence_of_element_located((By.XPATH, '//*[@id="queryLeftTable"]/tr')))
        except TimeoutException:
            print("查票信息加载超时！(120s)")


    def _order_ticket(self):

        tr_list = self.driver.find_elements(By.XPATH, '//*[@id="queryLeftTable"]/tr')  #获取所有列车车次
        for index, tr in enumerate(tr_list):
                # 获取 datatran 属性值并匹配
            if tr.get_attribute('datatran') == self.train_num:
                print("找到该列车！")
                print("车次:"+str(self.train_num)+"   上车站:"+str(self.from_station)+"   下车站:"+str(self.to_station)+"   出发日期:"+str(self.depart_time))
                # 获取上一个 tr 元素
                previous_tr = tr_list[index - 1]
                # 点击找到上一个 tr 中“预定”按钮
                # 找到上一个 tr 中“预定”按钮，等待直到a标签元素出现
                self.spinner.start()#启用等待动画
                WebDriverWait(previous_tr, 10000).until(
                    EC.element_to_be_clickable((By.XPATH, './/td[last()]/a'))
                )
                self.spinner.stop()
                previous_tr.find_element(By.XPATH, './/td[last()]/a').click()
                break

        try:
            WebDriverWait(self.driver,60).until(EC.url_to_be(self.order_url))
            # 选定乘车人
            self.driver.find_element(By.XPATH,f'//*[@id="normal_passenger_id"]/li/label[contains(text(),"{self.passenger}")]').click()
            #如果乘客是学生，对提示点击确定
            if EC.presence_of_element_located((By.XPATH, '//div[@id="dialog_xsertcj"]')):
                self.driver.find_element(By.ID,'dialog_xsertcj_ok').click()
                # 提交订单
                self.driver.find_element(By.ID,'submitOrder_id').click()
                try:
                    WebDriverWait(self.driver, 60).until(
                        EC.element_to_be_clickable((By.ID, 'qr_submit_id'))
                    )
                except TimeoutException:
                    print("加载超时！(60s)")
                # 点击确认
                #self.driver.find_element(By.ID,'qr_submit_id').click()
                print("购票成功！")
            else:
                # 提交订单
                self.driver.find_element(By.ID,'submitOrder_id').click()
                try:
                    WebDriverWait(self.driver, 60).until(
                        EC.element_to_be_clickable((By.ID, 'qr_submit_id'))
                    )
                except TimeoutException:
                    print("加载超时！(60s)")
                # 点击确认
                #self.driver.find_element(By.ID,'qr_submit_id').click()
                print("购票成功！")
        except TimeoutException:
            print("加载超时！(60s)")


    def run(self):
        #登录
        self._login()
        #进入购票页面
        self._enter_order_ticket()
        #查票
        self._search_ticket()
        #订票
        self._order_ticket()
        #关闭浏览器
        time.sleep(60)
        self.driver.quit()


class Spinner:#等待动画
    def __init__(self):
        self.animation = ['/', '——', '\\', '|']
        self.running = False
        self.thread = None
        self.message = ""

    def start(self, message="等待开票中"):
        """启动旋转动画并显示消息"""
        if not self.running:
            self.running = True
            self.message = message
            self.thread = threading.Thread(target=self._animate)
            self.thread.daemon = True  # 设置为守护线程
            self.thread.start()

    def stop(self):
        """停止旋转动画并清除显示内容"""
        self.running = False
        if self.thread:
            self.thread.join()
        sys.stdout.write(f'\r{" " * len(self.message)}\r')  # 清除文本
        sys.stdout.flush()

    def _animate(self):
        """动画执行逻辑"""
        while self.running:
            for frame in self.animation:
                sys.stdout.write(f'\r{self.message} {frame}')
                sys.stdout.flush()
                time.sleep(0.5)