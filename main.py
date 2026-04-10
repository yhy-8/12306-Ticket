from nicegui import ui
from app.web import WebApp

def main():
    print("正在初始化 12306 抢票助手...")
    # 实例化 WebApp，它会自动构建 UI 界面
    app = WebApp()

    # 启动 NiceGUI 界面，默认运行在 8080 端口
    # 关闭 reload 防止多线程下抢票任务被重载打断
    ui.run(title="12306 抢票助手", port=8080, reload=False, dark=False)

if __name__ in {"__main__", "__mp_main__"}:
    main()