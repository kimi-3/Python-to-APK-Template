# main.py：纯净版程序入口，整合UI、MQTT和日志展示
from kivy.config import Config

# 全局变量：存储接收的日志数据
recv_data_list = []

# 配置手机窗口尺寸（竖屏）
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '640')
Config.set('graphics', 'resizable', False)

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton
from kivymd.uix.scrollview import MDScrollView
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.image import Image
from kivymd.uix.textfield import MDTextField
from kivymd.toast import toast
import datetime
import json

# 导入MQTT工具类
from esp32_mqtt_utils import Esp32MqttClient

# 自定义无边界按钮（复用原有逻辑）
class NoBorderButton(MDBoxLayout):
    def __init__(self, text="按钮", button_type="normal",** kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint = (None, None)
        self.width = dp(80)
        self.height = dp(40)
        self.current_state = "关" if button_type == "switch" else "normal"
        self.is_disabled = False
        self.is_pressed = False
        
        self.label = MDLabel(
            text=text,
            font_size=dp(16),
            halign="center",
            valign="middle",
            font_name="CustomChinese" if "CustomChinese" in MDApp.get_running_app().theme_cls.font_styles else "Roboto"
        )
        self.add_widget(self.label)
        self.update_button_colors()

    def update_button_colors(self):
        if self.is_disabled:
            self.md_bg_color = (0.8, 0.8, 0.8, 1)
            self.label.text_color = (0.5, 0.5, 0.5, 1)
        elif self.is_pressed:
            self.md_bg_color = (0.2, 0.6, 1, 1)
            self.label.text_color = (1, 1, 1, 1)
        elif self.current_state == "开":
            self.md_bg_color = (0.1, 0.8, 0.1, 1)
            self.label.text_color = (1, 1, 1, 1)
        else:
            self.md_bg_color = (0.9, 0.9, 0.9, 1)
            self.label.text_color = (0, 0, 0, 1)

    def reset_button_state(self):
        self.is_pressed = False
        self.update_button_colors()

# 注册中文字体（适配打包）
def register_chinese_font():
    from kivy.core.text import LabelBase
    try:
        LabelBase.register(name='CustomChinese', fn_regular='simhei.ttf')
    except:
        # 打包时若没有自定义字体，使用默认
        LabelBase.register(name='CustomChinese', fn_regular='Roboto')

# 页面切换工具函数
def switch_page(app_instance, page_name):
    app_instance.page_container.clear_widgets()
    if page_name == "home":
        app_instance.current_page = create_home_page(app_instance)
    elif page_name == "me":
        app_instance.current_page = create_me_page(app_instance)
    app_instance.page_container.add_widget(app_instance.current_page)

# 首页构建
def create_home_page(app_instance):
    home_layout = MDBoxLayout(
        orientation="vertical",
        padding=dp(20),
        spacing=dp(20),
        size_hint_y=None,
    )
    home_layout.bind(minimum_height=home_layout.setter('height'))
    
    # 顶部栏：溶解氧 + 手动开关
    top_bar = MDBoxLayout(
        orientation="horizontal",
        spacing=dp(20),
        size_hint_y=None,
        height=dp(30)
    )
    do_label = MDLabel(
        text="溶解氧: 7.25mg/L",
        font_size=dp(18),
        font_name="CustomChinese",
        halign="left",
        valign="middle",
        theme_text_color="Custom",
        text_color=(0, 0, 1, 1)
    )
    ph_label = MDLabel(
        text="PH值: 7.0",
        font_size=dp(18),
        font_name="CustomChinese",
        theme_text_color="Custom",
        text_color=(0, 0, 1, 1)
    )
    temp_label = MDLabel(
        text="温度: 25.5℃",
        font_size=dp(18),
        font_name="CustomChinese",
        theme_text_color="Custom",
        text_color=(0, 0, 1, 1)
    )

    def update_sensor_ui(parsed_data):
        try:
            if "do" in parsed_data and parsed_data["do"] is not None:
                do_value = round(float(parsed_data["do"]), 2)
                do_label.text = f"溶解氧: {do_value}mg/L"
            if "ph" in parsed_data and parsed_data["ph"] is not None:
                ph_value = round(float(parsed_data["ph"]), 1)
                ph_label.text = f"PH值: {ph_value}"
            if "temp" in parsed_data and parsed_data["temp"] is not None:
                temp_value = round(float(parsed_data["temp"]), 1)
                temp_label.text = f"温度: {temp_value}℃"
        except (ValueError, TypeError):
            do_label.text = "溶解氧: 数据异常mg/L"
            ph_label.text = "PH值: 数据异常"
            temp_label.text = "温度: 数据异常℃"

    # 手动开关
    switch_label = MDLabel(
        text="手动开关",
        font_size=dp(16),
        halign="right",
        valign="middle",
        font_name="CustomChinese",
        size_hint_x=None,
        width=dp(80)
    )
    switch_btn = NoBorderButton(
        text="关",
        button_type="switch",
        size_hint_x=None,
        width=dp(60),
        size_hint_y=None,
        height=dp(30)
    )
    switch_btn.app_instance = app_instance

    def toggle_switch(instance):
        instance.current_state = "开" if instance.current_state == "关" else "关"
        instance.label.text = instance.current_state
        instance.update_button_colors()
        
        send_data = "yes" if instance.current_state == "开" else "no"
        cmd_desc = "启动" if instance.current_state == "开" else "停止"
        
        try:
            if not hasattr(instance, 'app_instance') or not instance.app_instance:
                raise Exception("未获取到APP实例")
            
            mqtt_client = instance.app_instance.mqtt_client
            if not mqtt_client:
                raise Exception("MQTT客户端未初始化")
            
            send_result = mqtt_client.publish_command("esp32/switch", send_data)
            if send_result:
                toast(f"设备{cmd_desc}成功")
            else:
                raise Exception("MQTT未连接")
        except Exception as e:
            error_msg = f"❌ 开关操作失败：{str(e)}"
            toast(error_msg)
            app_instance._update_recv_data(error_msg)

    switch_btn.bind(on_press=toggle_switch)
    top_bar.add_widget(do_label)
    top_bar.add_widget(switch_label)
    top_bar.add_widget(switch_btn)
    home_layout.add_widget(top_bar)

    # 阈值输入 + 确认按钮
    middle_layout = MDBoxLayout(
        orientation="horizontal",
        spacing=dp(20),
        size_hint_y=None,
        height=dp(100)
    )
    input_container = MDBoxLayout(
        orientation="vertical",
        spacing=dp(10),
        size_hint_x=1,
        size_hint_y=None,
        height=dp(120)
    )
    max_input = MDBoxLayout(
        orientation="horizontal",
        spacing=dp(10),
        size_hint_y=None,
        height=dp(40)
    )
    max_label = MDLabel(text="设置最高值:", font_size=dp(16), font_name="CustomChinese")
    max_textfield = MDTextField(hint_text="例如：8.0", size_hint_x=1)
    max_input.add_widget(max_label)
    max_input.add_widget(max_textfield)

    min_input = MDBoxLayout(
        orientation="horizontal",
        spacing=dp(10),
        size_hint_y=None,
        height=dp(40)
    )
    min_label = MDLabel(text="设置最低值:", font_size=dp(16), font_name="CustomChinese")
    min_textfield = MDTextField(hint_text="例如：6.0", size_hint_x=1)
    min_input.add_widget(min_label)
    min_input.add_widget(min_textfield)

    input_container.add_widget(max_input)
    input_container.add_widget(min_input)

    button_container = MDBoxLayout(
        orientation="vertical",
        spacing=dp(10),
        size_hint_x=None,
        width=dp(90),
        size_hint_y=None,
        height=dp(120)
    )
    confirm_btn = NoBorderButton(
        text="确认",
        size_hint_x=None,
        width=dp(90),
        size_hint_y=None,
        height=dp(40)
    )
    confirm_btn.app_instance = app_instance

    def on_confirm_click(instance):
        if instance.is_disabled:
            return
        
        instance.is_pressed = True
        instance.update_button_colors()
        
        max_val = max_textfield.text.strip()
        min_val = min_textfield.text.strip()
        
        try:
            float(max_val)
            float(min_val)
        except ValueError:
            error_msg = f"❌ 阈值输入无效：请输入数字"
            app_instance._update_recv_data(error_msg)
            toast(error_msg)
            Clock.schedule_once(lambda x: instance.reset_button_state(), 2)
            return
        
        try:
            threshold_data = json.dumps({
                "max_do": max_val,
                "min_do": min_val,
                "timestamp": str(datetime.datetime.now())
            }, ensure_ascii=False)
            
            mqtt_client = instance.app_instance.mqtt_client
            if not mqtt_client:
                raise Exception("MQTT客户端未初始化")
            
            send_result = mqtt_client.publish_command("esp32/threshold", threshold_data)
            if send_result:
                success_msg = f"✅ 阈值已发送：最高{max_val} | 最低{min_val}"
                app_instance._update_recv_data(success_msg)
                toast("阈值设置成功")
            else:
                raise Exception("MQTT未连接，发送失败")
        except Exception as e:
            error_msg = f"❌ 发送阈值失败：{str(e)}"
            app_instance._update_recv_data(error_msg)
            toast(error_msg)
        
        Clock.schedule_once(lambda x: instance.reset_button_state(), 2)
    
    confirm_btn.bind(on_press=on_confirm_click)
    button_container.add_widget(confirm_btn)
    middle_layout.add_widget(input_container)
    middle_layout.add_widget(button_container)
    home_layout.add_widget(middle_layout)

    # PH + 温度展示
    sensor_layout = MDBoxLayout(
        orientation="horizontal",
        spacing=dp(40),
        size_hint_y=None,
        height=dp(50)
    )
    sensor_layout.add_widget(ph_label)
    sensor_layout.add_widget(temp_label)
    home_layout.add_widget(sensor_layout)

    # PH安全范围图片（若没有图片可注释）
    ph_table_layout = MDBoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(230),
        pos_hint={"center_x": 0.55}
    )
    try:
        ph_table_image = Image(
            source="ph_safe_table.jpg",
            size_hint=(None, None),
            size=(dp(280), dp(280)),
            allow_stretch=True,
            keep_ratio=True
        )
        ph_table_layout.add_widget(ph_table_image)
    except:
        ph_table_layout.add_widget(MDLabel(text="PH安全范围：6~9", font_size=dp(16), font_name="CustomChinese"))
    home_layout.add_widget(ph_table_layout)

    ph_note_label = MDLabel(
        text="PH值安全范围在6~9",
        font_size=dp(16),
        font_name="CustomChinese",
        halign="center",
        bold=True,
        size_hint_y=None,
        height=dp(30)
    )
    home_layout.add_widget(ph_note_label)

    return home_layout

# 个人中心页面（含完整日志展示）
def create_me_page(app_instance):
    me_layout = MDBoxLayout(
        orientation="vertical",
        padding=dp(20),
        spacing=dp(15),
        size_hint_y=None,
    )
    me_layout.bind(minimum_height=me_layout.setter('height'))
    
    me_layout.add_widget(MDLabel(
        text="我的个人中心",
        font_size=dp(20),
        font_name="CustomChinese",
        halign="center",
        bold=True,
        size_hint_y=None,
        height=dp(60)
    ))
    
    # 连接状态
    if hasattr(app_instance, 'mqtt_client') and app_instance.mqtt_client:
        connect_status = "已连接" if app_instance.mqtt_client.connected else "未连接"
        status_color = (0, 0.8, 0, 1) if app_instance.mqtt_client.connected else (0.8, 0, 0, 1)
    else:
        connect_status = "未初始化"
        status_color = (0.5, 0.5, 0.5, 1)
    
    status_label = MDLabel(
        text=f"服务器连接状态: {connect_status}",
        font_size=dp(16),
        font_name="CustomChinese",
        theme_text_color="Custom",
        text_color=status_color,
        size_hint_y=None,
        height=dp(40)
    )
    me_layout.add_widget(status_label)
    
    # 设备信息
    me_layout.add_widget(MDLabel(
        text="设备编号：DEV-20260111",
        font_size=dp(16),
        font_name="CustomChinese",
        size_hint_y=None,
        height=dp(30)
    ))
    me_layout.add_widget(MDLabel(
        text="当前在线：是",
        font_size=dp(16),
        font_name="CustomChinese",
        size_hint_y=None,
        height=dp(30)
    ))

    # 运行日志区域
    me_layout.add_widget(MDLabel(
        text="运行日志",
        font_size=dp(18),
        font_name="CustomChinese",
        bold=True,
        size_hint_y=None,
        height=dp(40)
    ))
    log_scroll_view = ScrollView(
        size_hint=(1, None),
        height=dp(200),
        do_scroll_x=False
    )
    log_label = MDLabel(
        text="\n".join(recv_data_list) + "\n", 
        font_name="CustomChinese", 
        size_hint_y=None,
        valign="top",
        halign="left"
    )
    log_label.is_log_label = True  # 标记为日志标签
    log_label.bind(texture_size=log_label.setter('size'))
    log_scroll_view.add_widget(log_label)
    me_layout.add_widget(log_scroll_view)

    return me_layout

# 整体UI构建
def create_app_ui(app_instance):
    Window.orientation = 'portrait'
    register_chinese_font()

    # 主题配置
    app_instance.theme_cls.primary_palette = "Blue"
    app_instance.theme_cls.theme_style = "Light"

    # 主容器
    main_container = MDBoxLayout(
        orientation="vertical",
        padding=0,
        spacing=0,
        size_hint=(1, 1)
    )

    # 页面容器
    app_instance.page_container = MDScrollView(
        do_scroll_x=False,
        do_scroll_y=False,
        size_hint=(1, 1)
    )
    app_instance.current_page = create_home_page(app_instance)
    app_instance.page_container.add_widget(app_instance.current_page)
    main_container.add_widget(app_instance.page_container)

    # 底部导航栏
    bottom_nav_bar = MDBoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(60),
        padding=[dp(60), dp(5), dp(60), dp(5)],
        spacing=Window.size[0] * 0.2,
        md_bg_color=(1, 1, 1, 1)
    )
    with bottom_nav_bar.canvas.before:
        Color(0, 0, 0, 0.1)
        Rectangle(pos=(bottom_nav_bar.x, bottom_nav_bar.y + bottom_nav_bar.height), size=(bottom_nav_bar.width, 2))

    # 首页导航
    nav_item1 = MDBoxLayout(orientation="vertical", size_hint_x=1, spacing=dp(2))
    nav_item1_icon = MDIconButton(icon="home", size_hint=(None, None), size=(dp(24), dp(24)), md_bg_color=(1,1,1,0))
    nav_item1_icon.bind(on_press=lambda x: switch_page(app_instance, "home"))
    nav_item1_text = MDLabel(text="首页", font_size=dp(12), font_name="CustomChinese", halign="center")
    nav_item1.add_widget(nav_item1_icon)
    nav_item1.add_widget(nav_item1_text)

    # 个人中心导航
    nav_item2 = MDBoxLayout(orientation="vertical", size_hint_x=1, spacing=dp(2))
    nav_item2_icon = MDIconButton(icon="account-circle", size_hint=(None, None), size=(dp(24), dp(24)), md_bg_color=(1,1,1,0))
    nav_item2_icon.bind(on_press=lambda x: switch_page(app_instance, "me"))
    nav_item2_text = MDLabel(text="我", font_size=dp(12), font_name="CustomChinese", halign="center")
    nav_item2.add_widget(nav_item2_icon)
    nav_item2.add_widget(nav_item2_text)

    bottom_nav_bar.add_widget(nav_item1)
    bottom_nav_bar.add_widget(nav_item2)
    main_container.add_widget(bottom_nav_bar)

    return main_container

# 主APP类
class Esp32MobileApp(MDApp):
    def __init__(self,** kwargs):
        super().__init__(**kwargs)
        # MQTT配置（替换为你的实际配置）
        self.mqtt_config = {
            "broker": "iaa16ebf.ala.cn-hangzhou.emqxsl.cn",
            "port": 8883,
            "username": "esp32",
            "password": "123456"
        }
        self.mqtt_client = None
        self.page_container = None
        self.current_page = None

    def build(self):
        main_layout = create_app_ui(self)
        # 延长初始化延迟（适配手机）
        Clock.schedule_once(lambda dt: self._init_mqtt_client(), 3)
        return main_layout

    def _init_mqtt_client(self):
        """初始化MQTT客户端"""
        self.mqtt_client = Esp32MqttClient(
            broker=self.mqtt_config["broker"],
            port=self.mqtt_config["port"],
            username=self.mqtt_config["username"],
            password=self.mqtt_config["password"],
            data_callback=self._update_recv_data
        )
        self.mqtt_client.start_mqtt()

    def _update_recv_data(self, content):
        """更新个人中心日志"""
        global recv_data_list
        recv_data_list.append(content)
        if len(recv_data_list) > 20:
            recv_data_list = recv_data_list[-20:]
        
        # 仅在个人中心页面更新UI
        if hasattr(self, 'current_page') and self.current_page:
            for child in self.current_page.walk():
                if isinstance(child, MDLabel) and hasattr(child, 'is_log_label') and child.is_log_label:
                    child.text = "\n".join(recv_data_list) + "\n"
                    # 自动滚动到底部
                    for parent in child.parent.walk():
                        if isinstance(parent, ScrollView):
                            parent.scroll_y = 0
                            break

    def update_me_page_status(self):
        """更新个人中心连接状态"""
        if hasattr(self, 'current_page') and self.current_page and "我的个人中心" in [c.text for c in self.current_page.children if isinstance(c, MDLabel)]:
            self.page_container.clear_widgets()
            self.current_page = create_me_page(self)
            self.page_container.add_widget(self.current_page)

# 适配dp单位（避免打包后单位异常）
def dp(value):
    from kivy.metrics import dp as kivy_dp
    return kivy_dp(value)

if __name__ == "__main__":
    Esp32MobileApp().run()