# 基于抓包的12306抢票脚本
## 一、所需环境（由pipreqs导出得到）
python==3.12.7  
jupyter_core==5.7.2  
ntplib==0.4.0  
numpy==2.2.2  
Pillow==11.1.0  
Requests==2.32.3    
tkcalendar==1.6.1
## 二、如何使用
1、启动`ui.py`，在出现的ui窗口中登录，填入信息并点击开始抢票即可  
2、在`user.py`里可以修改参数。包括：ntp服务器地址、抢票尝试次数、是否开启日志文本记录、提前请求时间、是否启用座位选择、ntp授时校准时的请求次数、 各部分函数最多循环次数  
3、在ui界面里，选择除了成人票以外的其他类型时，请确保已经通过认证，否则可能导致出票失败
### 注意：由于代码的抓包响应是固定的，如果12306对接口参数进行修改则代码很可能失效！截止到目前:2025-02-02，代码仍然有效！
## 三、相关说明
### 1、版权说明
本项目是基于开源项目(https://github.com/shaocuirong/12306-)改进而来，修补了已知bug，完善ui，加入了更多功能
### 2、些许代码细节和原理细节
#### (1)初步获取cookies
通过21年的[帖子](https://blog.csdn.net/qq_46092061/article/details/119967871)得知可以访问：  
https://www.12306.cn/index/  
https://kyfw.12306.cn/otn/login/conf  
https://kyfw.12306.cn/otn/index12306/getLoginBanner   
这三个网站去初步获取cookies，但实际测试下来，主要是得获取`JSESSIONID`这个参数（只能通过第三个请求获取）其他的都一样  
#### (2)扫码登录
通过访问(https://kyfw.12306.cn/passport/web/create-qr64)获取二维码和其uuid（后面检查二维码状态用）  
获取二维码后，每隔3秒访问(https://kyfw.12306.cn/passport/web/checkqr)检查是否完成登录  
#### (3)对于报错自动处理
`user.py`里有两个次数设置，`max_try_times`是整体抢票流程的最多重复次数，`grabfunction_max_try_times`是抢票各部分函数内部循环出错后最多重复执行的次数   
但大部分出错都是返回“服务器繁忙”，这种情况连续5次，服务器会主动断开连接，此时即便函数内循环次数设置超过5次，也会被强制退出函数，并重新循环整个抢票流程 
#### (4)对于时间模式
两个模式：本地时间模式和NTP授时校准  
默认自动切入NTP授时校准，只有NTP服务器访问失败才切换为本地模式  
为了保证精准度，只有在开票前1分钟才尝试切换为ntp授时校准  
但再准时发包都不如提前发包，若提前发包达到5次无效返回，服务器就会自动断开连接！  
**提前发包属于高风险高收益！**
#### (5)对于相应接口参数的分析
使用fiddler跑一次，得出所有的请求data和回复response后，便可得到所有参数  
进一步分析12306网页的源代码的js文件，通过直接查找对应参数名称分析该参数  
例如：[确认订单](https://kyfw.12306.cn/otn/confirmPassenger/confirmSingleForQueue)的请求data里的choose_seat参数，在`passengerInfo_js.js`文件中有相应的赋值关系
### 3、对于fiddler的使用
具体使用详细见[抓包分析](https://blog.csdn.net/Mubei1314/article/details/122389950)   
主要流程：抓包、分析协议头、用python伪装浏览器发送请求  
如何对12306的网页和相关请求分析，同上的[帖子](https://blog.csdn.net/qq_46092061/article/details/119967871)介绍有，虽然很多接口的参数已经不能用了，但也能作为一个参考  
开着fiddler在网页端走一遍购票流程，即可保存相应的包信息

