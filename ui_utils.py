# ui_utils.py：UI通用工具（组件、字体、页面切换）
from kivymd.uix.label import MDLabel
from kivy.uix.button import ButtonBehavior
from kivy.core.text import LabelBase
from kivy.metrics import dp
from kivy.clock import Clock

# 通用按钮组件（原有，保持不变）
class NoBorderButton(ButtonBehavior, MDLabel):
    def __init__(self, **kwargs):
        self.button_type = kwargs.pop("button_type", "normal")
        super().__init__(**kwargs)
        self.font_name = "CustomChinese"
        self.halign = "center"
        self.valign = "middle"
        self.font_size = dp(16)
        
        if self.button_type == "switch":
            self.state_colors = {
                "关": {"bg": (0.8, 0.8, 0.8, 1), "text": (0, 0, 0, 1)},
                "开": {"bg": (0.8, 0.2, 0.2, 1), "text": (1, 1, 1, 1)}
            }
            self.current_state = "关"
        else:
            self.normal_colors = {"bg": (0.8, 0.8, 0.8, 1), "text": (0, 0, 0, 1)}
            self.pressed_colors = {"bg": (0.2, 0.5, 0.8, 1), "text": (1, 1, 1, 1)}
            self.is_pressed = False
        
        self.is_disabled = False
        self.update_button_colors()

    def update_button_colors(self):
        if self.is_disabled:
            self.md_bg_color = (0.9, 0.9, 0.9, 1)
            self.text_color = (0.5, 0.5, 0.5, 1)
            self.disabled = True
        else:
            if self.button_type == "switch":
                self.md_bg_color = self.state_colors[self.current_state]["bg"]
                self.text_color = self.state_colors[self.current_state]["text"]
            else:
                if self.is_pressed:
                    self.md_bg_color = self.pressed_colors["bg"]
                    self.text_color = self.pressed_colors["text"]
                else:
                    self.md_bg_color = self.normal_colors["bg"]
                    self.text_color = self.normal_colors["text"]
            self.disabled = False

    def reset_button_state(self):
        if self.button_type != "switch":
            self.is_pressed = False
            self.update_button_colors()

# 注册中文字体（原有，保持不变）
def register_chinese_font():
    LabelBase.register(
        name="CustomChinese",
        fn_regular="Font_0.ttf"
    )

# 页面切换工具函数（完善路由：新增history页面）
# ui_utils.py：修改switch_page函数中"me"分支
def switch_page(app_instance, page_name):
    # 延迟导入避免循环依赖
    from app_ui_pages import create_home_page, create_me_page, create_history_page
    app_instance.page_container.clear_widgets()
    if page_name == "home":
        app_instance.current_page = create_home_page(app_instance)
    elif page_name == "me":
        app_instance.current_page = create_me_page(app_instance)  # 传递app_instance
    elif page_name == "history":
        app_instance.current_page = create_history_page(app_instance)
    app_instance.page_container.add_widget(app_instance.current_page)