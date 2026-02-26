import datetime
from kivy.config import Config
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDIconButton
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivymd.uix.scrollview import MDScrollView
from ui_utils import NoBorderButton
import json
from kivymd.toast import toast

# ======================== 全局变量：存储历史数据（新增，用于记录真实传感器数据） ========================
# 初始化历史数据列表，保留原测试数据格式，后续用真实数据填充
GLOBAL_HISTORY_DATA = []

# ======================== 页面构建逻辑（原pages.py内容，仅修改数据相关部分） ========================
def create_home_page(app_instance):
    home_layout = MDBoxLayout(
        orientation="vertical",
        padding=dp(20),
        spacing=dp(20),
        size_hint_y=None,
    )
    home_layout.bind(minimum_height=home_layout.setter('height'))

    # ========== 顶部栏：溶解氧 + 手动开关 ==========
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
    # 【修改1：删除原有模拟数据更新逻辑，替换为MQTT真实数据更新+历史数据记录】
    def update_sensor_ui_and_record_history(parsed_data):
        """
        新增：更新UI标签 + 记录历史数据（保留原格式，不改动页面布局）
        """
        try:
            # 1. 更新溶解氧（保留原格式：xxxmg/L，无空格）
            if "do" in parsed_data and parsed_data["do"] is not None:
                do_value = round(float(parsed_data["do"]), 2)
                do_label.text = f"溶解氧: {do_value}mg/L"  # 与原页面格式一致
            # 2. 更新PH值（保留原格式：xxx，无额外后缀）
            if "ph" in parsed_data and parsed_data["ph"] is not None:
                ph_value = round(float(parsed_data["ph"]), 1)
                ph_label.text = f"PH值: {ph_value}"  # 与原页面格式一致
            # 3. 更新温度（保留原格式：xxx℃，无空格）
            if "temp" in parsed_data and parsed_data["temp"] is not None:
                temp_value = round(float(parsed_data["temp"]), 1)
                temp_label.text = f"温度: {temp_value}℃"  # 与原页面格式一致

            # 4. 新增：记录历史数据（匹配原历史页面的数据格式）
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            do_val = do_label.text.replace("溶解氧: ", "").replace("mg/L", "")
            ph_val = ph_label.text.replace("PH值: ", "")
            temp_val = temp_label.text.replace("温度: ", "").replace("℃", "")
            history_record = f"{current_time}: 溶解氧{do_val}mg/L | PH{ph_val} | 温度{temp_val}℃"
            
            # 插入到列表头部（最新数据在前），保留最多20条记录
            GLOBAL_HISTORY_DATA.insert(0, history_record)
            if len(GLOBAL_HISTORY_DATA) > 20:
                GLOBAL_HISTORY_DATA.pop()

        except (ValueError, TypeError):
            # 数据异常时保留原标签格式，仅提示异常
            do_label.text = "溶解氧: 数据异常mg/L"
            ph_label.text = "PH值: 数据异常"
            temp_label.text = "温度: 数据异常℃"

    # 【修改2：注册MQTT回调，绑定真实数据更新函数】
    if app_instance and hasattr(app_instance, 'mqtt_client') and app_instance.mqtt_client:
        app_instance.mqtt_client.set_parsed_data_callback(update_sensor_ui_and_record_history)

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
    # 新增：给开关按钮绑定app_instance，用于获取MQTT客户端
    switch_btn.app_instance = app_instance

    def toggle_switch(instance):
        # 1. 原有：切换开关状态
        instance.current_state = "开" if instance.current_state == "关" else "关"
        instance.text = instance.current_state
        instance.update_button_colors()
        
        # 2. 新增：映射状态到发送数据
        send_data = "yes" if instance.current_state == "开" else "no"
        cmd_desc = "设备启动" if instance.current_state == "开" else "设备停止"
        print(f"向ESP32发送指令：{cmd_desc}（对应数据：{send_data}）")
        
        # 3. 新增：发送数据到MQTT服务器
        try:
            if not hasattr(instance, 'app_instance') or not instance.app_instance:
                raise Exception("未获取到APP实例，无法发送数据")
            
            mqtt_client = instance.app_instance.mqtt_client
            if not mqtt_client:
                raise Exception("MQTT客户端未初始化，无法发送数据")
            
            # 发布到开关专属主题，便于服务器识别
            send_topic = "esp32/switch"
            send_result = mqtt_client.publish_command(send_topic, send_data)
            
            if send_result:
                print(f"✅ 开关状态数据发送成功：{send_data}（主题：{send_topic}）")
                toast(f"she{send_data}")
               
            else:
                raise Exception("MQTT未连接，数据发送失败")
        
        except Exception as e:
            error_msg = f"❌ 开关状态数据发送失败：{str(e)}"
            print(error_msg)

    switch_btn.bind(on_press=toggle_switch)

    top_bar.add_widget(do_label)
    top_bar.add_widget(switch_label)
    top_bar.add_widget(switch_btn)
    home_layout.add_widget(top_bar)

    # ========== 中间区域：阈值输入框 + 按钮列 ==========
    # 【完全保留原代码，无任何修改】
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
    max_textfield = MDTextField(hint_text="", size_hint_x=1)
    max_input.add_widget(max_label)
    max_input.add_widget(max_textfield)

    min_input = MDBoxLayout(
        orientation="horizontal",
        spacing=dp(10),
        size_hint_y=None,
        height=dp(40)
    )
    min_label = MDLabel(text="设置最低值:", font_size=dp(16), font_name="CustomChinese")
    min_textfield = MDTextField(hint_text="", size_hint_x=1)
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
    def check_input_validity(*args):
        max_val = max_textfield.text.strip()
        min_val = min_textfield.text.strip()
        confirm_btn.is_disabled = (not max_val) or (not min_val)
        confirm_btn.update_button_colors()
    max_textfield.bind(text=check_input_validity)
    min_textfield.bind(text=check_input_validity)
    check_input_validity()

    # 确认按钮点击事件
    def on_confirm_click(instance):
        if instance.is_disabled:
            return
        
        instance.is_pressed = True
        instance.update_button_colors()
        
        max_val = max_textfield.text.strip()
        min_val = min_textfield.text.strip()
        
        # 校验输入是否为数字
        try:
            float(max_val)
            float(min_val)
        except ValueError:
            print(f"❌ 阈值输入无效：最高值={max_val}，最低值={min_val}（必须是数字）")
            if hasattr(instance, 'app_instance') and instance.app_instance:
                instance.app_instance._update_recv_data(f"❌ 阈值输入无效：请输入数字（当前最高={max_val}，最低={min_val}）")
            Clock.schedule_once(lambda x: instance.reset_button_state(), 2)
            return
        
        print(f"保存阈值：最高值={max_val}，最低值={min_val}")
        
        # 构造JSON数据
        try:
            threshold_data = json.dumps({
                "max_do": max_val,
                "min_do": min_val,
                "timestamp": str(datetime.datetime.now())
            }, ensure_ascii=False)
        except Exception as e:
            print(f"❌ 构造JSON数据失败：{str(e)}")
            if hasattr(instance, 'app_instance') and instance.app_instance:
                instance.app_instance._update_recv_data(f"❌ 数据格式错误：{str(e)}")
            Clock.schedule_once(lambda x: instance.reset_button_state(), 2)
            return
        
        # 发送数据到服务器
        try:
            if not hasattr(instance, 'app_instance') or not instance.app_instance:
                raise Exception("未获取到APP实例，无法连接MQTT客户端")
            
            mqtt_client = instance.app_instance.mqtt_client
            if not mqtt_client:
                raise Exception("MQTT客户端未初始化")
            
            send_result = mqtt_client.publish_command("esp32/threshold", threshold_data)
            if send_result:
                print(f"✅ 阈值数据已发送：{threshold_data}")
                instance.app_instance._update_recv_data(f"✅ 阈值已发送：最高{max_val} | 最低{min_val}")
            else:
                raise Exception("MQTT未连接，发送失败")
        
        except Exception as e:
            error_msg = f"❌ 发送阈值失败：{str(e)}"
            print(error_msg)
            if hasattr(instance, 'app_instance') and instance.app_instance:
                instance.app_instance._update_recv_data(error_msg)
        
        Clock.schedule_once(lambda x: instance.reset_button_state(), 2)
    
    # 绑定APP实例和点击事件
    confirm_btn.app_instance = app_instance
    confirm_btn.bind(on_press=on_confirm_click)

    # 历史数据按钮
    history_btn = NoBorderButton(
        text="历史数据",
        size_hint_x=None,
        width=dp(90),
        size_hint_y=None,
        height=dp(40)
    )
    def on_history_click(instance):
        instance.is_pressed = True
        instance.update_button_colors()
        print("准备切换到历史数据页面")
        from ui_utils import switch_page
        switch_page(app_instance, "history")
        Clock.schedule_once(lambda x: instance.reset_button_state(), 2)
    history_btn.bind(on_press=on_history_click)

    button_container.add_widget(confirm_btn)
    button_container.add_widget(history_btn)
    middle_layout.add_widget(input_container)
    middle_layout.add_widget(button_container)
    home_layout.add_widget(middle_layout)

    # ========== 底部：PH值 + 温度展示 ==========
    sensor_layout = MDBoxLayout(
        orientation="horizontal",
        spacing=dp(40),
        size_hint_y=None,
        height=dp(50)
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
    sensor_layout.add_widget(ph_label)
    sensor_layout.add_widget(temp_label)
    home_layout.add_widget(sensor_layout)

    # ========== PH安全范围说明 + 图片 ==========
    # 【完全保留原代码，无任何修改】
    ph_table_layout = MDBoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(230),
        pos_hint={"center_x": 0.55}
    )
    ph_table_image = Image(
        source="ph_safe_table.jpg",
        size_hint=(None, None),
        size=(dp(280), dp(280)),
        allow_stretch=True,
        keep_ratio=True
    )
    ph_table_layout.add_widget(ph_table_image)
    home_layout.add_widget(ph_table_layout)

    ph_note_layout = MDBoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(10)
    )
    ph_note_label = MDLabel(
        text="PH值安全范围在6~9",
        font_size=dp(16),
        font_name="CustomChinese",
        halign="center",
        bold=True
    )
    ph_note_layout.add_widget(ph_note_label)
    home_layout.add_widget(ph_note_layout)

    return home_layout

def create_history_page(app_instance):
    # 历史数据页面根布局（保留原布局，仅修改数据来源）
    history_layout = MDBoxLayout(
        orientation="vertical",
        padding=dp(20),
        spacing=dp(10),
        size_hint=(1, 1),
    )

    # 页面标题（保留原样式，无修改）
    history_title = MDLabel(
        text="设备历史数据",
        font_size=dp(22),
        font_name="CustomChinese",
        halign="center",
        bold=True,
        size_hint_y=None,
        height=dp(60)
    )
    history_layout.add_widget(history_title)

    # 滚动视图（保留原样式，无修改）
    scroll_view = ScrollView(
        size_hint=(1, 1),
        do_scroll_x=False,
        scroll_type=['content', 'bars'],
        bar_width=dp(1),
        bar_color=(0.3, 0.3, 0.3, 1),
        bar_inactive_color=(0.8, 0.8, 0.8, 1),
        always_overscroll=True,
        scroll_wheel_distance=dp(20)
    )

    # 滚动内容容器（保留原样式，无修改）
    scroll_content = MDBoxLayout(
        orientation="vertical",
        spacing=dp(10),
        size_hint=(1, None),
        padding=dp(5)
    )
    scroll_content.bind(minimum_height=scroll_content.setter('height'))

    # 【修改3：替换数据来源，用真实记录的GLOBAL_HISTORY_DATA替代模拟数据】
    # 若没有真实数据，显示默认提示，否则显示真实记录
    display_data = GLOBAL_HISTORY_DATA if len(GLOBAL_HISTORY_DATA) > 0 else [
        "暂无历史数据，请先等待设备上传数据...",
        "2026-01-11 16:00: 溶解氧7.25mg/L | PH7.0 | 温度25.5℃"  # 保留一条默认数据保持格式
    ]

    # 添加数据到滚动容器（保留原样式，仅修改数据列表）
    for idx, data in enumerate(display_data):
        data_label = MDLabel(
            text=data,
            font_size=dp(16),
            font_name="CustomChinese",
            halign="left",
            size_hint_y=None,
            height=dp(40),
            theme_text_color="Custom",
            text_color=(0.2, 0.2, 0.2, 1) if idx != 0 or len(GLOBAL_HISTORY_DATA) > 0 else (0.8, 0, 0, 1),
            valign="middle",
        )
        scroll_content.add_widget(data_label)

    scroll_view.add_widget(scroll_content)
    history_layout.add_widget(scroll_view)

    return history_layout

def create_me_page(app_instance):
    # 【完全保留原代码，无任何修改】
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
        halign="center",
        font_name="CustomChinese",
        bold=True
    ))
    
    # 显示MQTT连接状态
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
        text_color=status_color
    )
    me_layout.add_widget(status_label)
    
    me_layout.add_widget(MDLabel(
        text="设备编号：DEV-20260111",
        font_size=dp(16),
        font_name="CustomChinese"
    ))
    me_layout.add_widget(MDLabel(
        text="当前在线：是",
        font_size=dp(16),
        font_name="CustomChinese"
    ))
    return me_layout

# ======================== UI构建逻辑（原esp32_app_ui.py内容，完全保留无修改） ========================
def create_app_ui(app_instance):
    # 基础配置
    Window.orientation = 'portrait'
    screen_width, screen_height = Window.size
    print(f"当前设备屏幕尺寸：{screen_width}×{screen_height}px")
    
    # 注册中文字体（依赖ui_utils中的方法）
    from ui_utils import register_chinese_font
    register_chinese_font()

    # 主题配置
    app_instance.theme_cls.primary_palette = "Blue"
    app_instance.theme_cls.theme_style = "Light"
    app_instance.theme_cls.font_styles.update({
        "H5": [ "CustomChinese", 24, False, 0.15 ],
        "Body1": [ "CustomChinese", 14, False, 0.15 ]
    })

    # 主容器
    main_container = MDBoxLayout(
        orientation="vertical",
        padding=0,
        spacing=0,
        size_hint=(1, 1)
    )

    # 页面容器（用于切换首页/个人中心）
    app_instance.page_container = MDScrollView(
        do_scroll_x=False,
        do_scroll_y=False,
        size_hint=(1, 1),
        pos_hint={"top": 1.0}
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
        spacing=screen_width * 0.2,
        md_bg_color=(1, 1, 1, 1),
        pos_hint={"center_x": 0.5, "y": 0.0}
    )
    # 导航栏阴影
    with bottom_nav_bar.canvas.before:
        Color(0, 0, 0, 0.1)
        Rectangle(
            pos=(bottom_nav_bar.x, bottom_nav_bar.y + bottom_nav_bar.height),
            size=(bottom_nav_bar.width, 2)
        )
    # 首页导航项
    nav_item1 = MDBoxLayout(
        orientation="vertical",
        size_hint_x=1,
        spacing=dp(2),
        pos_hint={"center_x": 0.5, "center_y": 0.5}
    )
    nav_item1_icon = MDIconButton(
        icon="home",
        size_hint=(None, None),
        size=(dp(24), dp(24)),
        pos_hint={"center_x": 0.5},
        md_bg_color=(1, 1, 1, 0),
        text_color=(0, 0, 0, 1)
    )
    from ui_utils import switch_page
    nav_item1_icon.bind(on_press=lambda x: switch_page(app_instance, "home"))
    nav_item1_text = MDLabel(
        text="首页",
        font_size=dp(12),
        font_name="CustomChinese",
        halign="center",
        color=(0, 0, 0, 1)
    )
    nav_item1.add_widget(nav_item1_icon)
    nav_item1.add_widget(nav_item1_text)

    # 个人中心导航项
    nav_item2 = MDBoxLayout(
        orientation="vertical",
        size_hint_x=1,
        spacing=dp(2),
        pos_hint={"center_x": 0.5, "center_y": 0.5}
    )
    nav_item2_icon = MDIconButton(
        icon="account-circle",
        size_hint=(None, None),
        size=(dp(24), dp(24)),
        pos_hint={"center_x": 0.5},
        md_bg_color=(1, 1, 1, 0),
        text_color=(0, 0, 0, 1)
    )
    nav_item2_icon.bind(on_press=lambda x: switch_page(app_instance, "me"))
    nav_item2_text = MDLabel(
        text="我",
        font_size=dp(12),
        font_name="CustomChinese",
        halign="center",
        color=(0, 0, 0, 1)
    )
    nav_item2.add_widget(nav_item2_icon)
    nav_item2.add_widget(nav_item2_text)

    bottom_nav_bar.add_widget(nav_item1)
    bottom_nav_bar.add_widget(nav_item2)
    
    # 绑定接收数据的Label（供main.py更新UI）
    app_instance.recv_label = MDLabel(text="", font_name="CustomChinese")
    main_container.add_widget(bottom_nav_bar)

    return main_container