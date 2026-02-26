# main.py：主运行文件，程序入口，整合UI、MQTT和业务逻辑
from kivy.config import Config

# 全局变量：存储接收的数据（用于UI展示）
recv_data_list = []

# 配置模拟窗口尺寸（手机竖屏：宽360px，高640px）
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '640')
# 禁止窗口缩放，保持手机比例
Config.set('graphics', 'resizable', False)
from kivymd.app import MDApp
# 导入MQTT工具类
from esp32_mqtt_utils import Esp32MqttClient
# 核心修改：从合并后的app_ui_pages.py导入UI构建方法（替代原esp32_app_ui.py）
from app_ui_pages import create_app_ui
from kivymd.uix.label import MDLabel


class Esp32MobileApp(MDApp):
    def __init__(self,** kwargs):
        super().__init__(**kwargs)
        # 1. MQTT配置信息  
        self.mqtt_config = {
            "broker": "iaa16ebf.ala.cn-hangzhou.emqxsl.cn",
            "port": 8883,
            "username": "esp32",
            "password": "123456"
        }
        # 2. 初始化属性（UI控件、MQTT客户端）
        self.mqtt_client = None
        self.scroll_view = None  # 初始化为None
        self.recv_label = None   # 初始化为None
        self.cmd_input = None    # 初始化为None

    def build(self):
        """程序构建入口：先创建UI，再启动MQTT"""
        # 1. 先构建UI并获取控件引用
        main_layout = create_app_ui(self)
        # 2. 等待UI初始化完成后，再启动MQTT连接（关键修改）
        self._init_mqtt_client()
        return main_layout

    def _init_mqtt_client(self):
        """初始化MQTT客户端"""
        self.mqtt_client = Esp32MqttClient(
            broker=self.mqtt_config["broker"],
            port=self.mqtt_config["port"],
            username=self.mqtt_config["username"],
            password=self.mqtt_config["password"],
            data_callback=self._update_recv_data  # 这里改为已定义的_update_recv_data
        )
        # 启动MQTT通信
        self.mqtt_client.start_mqtt()

    # main.py：修改_update_recv_data方法
    def _update_recv_data(self, content):
        """更新UI数据（增加控件是否初始化的判断）"""
        # 关键修改：先判断UI控件是否已初始化
        if not all([self.scroll_view, self.recv_label]):
            print(f"UI未就绪，暂存消息：{content}")
            return

        global recv_data_list
        recv_data_list.append(content)
        # 限制数据条数，避免内存溢出
        if len(recv_data_list) > 20:
            recv_data_list = recv_data_list[-20:]
        # 更新UI文本
        self.recv_label.text = "\n".join(recv_data_list) + "\n"
        # 自动滚动到最新数据
        self.scroll_view.scroll_y = 0
    
        # 新增：如果是连接状态相关消息，更新个人中心
        if "MQTT连接成功" in content or "MQTT连接失败" in content or "连接异常" in content:
            self.update_me_page_status()

    def _on_send_cmd_click(self, instance):
        """发送按钮点击事件"""
        # 1. 验证输入指令
        cmd = self.cmd_input.text.strip()
        if not cmd:
            self._update_recv_data("❌ 请输入有效指令（pause/resume）")
            return
        if cmd not in ["pause", "resume"]:
            self._update_recv_data("❌ 仅支持pause/resume指令")
            return
        # 2. 发布指令到ESP32
        self.mqtt_client.publish_command("esp32/control", cmd)
        # 3. 清空输入框
        self.cmd_input.text = ""
    
    # main.py：在Esp32MobileApp类中新增方法
    def update_me_page_status(self):
        """更新个人中心的连接状态（如果当前页面是个人中心）"""
        if hasattr(self, 'current_page') and "我的个人中心" in [child.text for child in self.current_page.children if isinstance(child, MDLabel)]:
            # 重新构建个人中心页面（触发状态刷新）
            # 核心修改：从合并后的app_ui_pages.py导入create_me_page（替代原pages.py）
            from app_ui_pages import create_me_page
            self.page_container.clear_widgets()
            self.current_page = create_me_page(self)
            self.page_container.add_widget(self.current_page)

if __name__ == "__main__":
    """程序入口：启动APP主循环"""
    Esp32MobileApp().run()