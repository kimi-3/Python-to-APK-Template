# esp32_mqtt_utils.py：纯净版MQTT工具类，带全量异常日志
import paho.mqtt.client as mqtt
import ssl
import time
from kivy.clock import Clock

class Esp32MqttClient:
    def __init__(self, broker, port, username, password, data_callback=None, max_reconnect_attempts=5):
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.data_callback = data_callback  # 日志回调
        
        self.mqtt_client = None
        self.connected = False
        self.reconnect_count = 0
        self.max_reconnect_attempts = max_reconnect_attempts

    def init_mqtt_client(self):
        """初始化MQTT客户端（带异常捕获）"""
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.username_pw_set(self.username, self.password)
            
            # TLS配置（适配手机，临时禁用证书验证）
            self.mqtt_client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
            self.mqtt_client.tls_insecure_set(True)  # 测试用，正式环境可删除
            
            # 绑定回调
            self.mqtt_client.on_connect = self._on_connect
            self.mqtt_client.on_disconnect = self._on_disconnect
            self.mqtt_client.on_message = self._on_message
            
            # 超时配置
            self.mqtt_client.keepalive = 30
            self.mqtt_client.connect_timeout = 10
            
            self._log_msg(f"✅ MQTT客户端初始化完成")
        except Exception as e:
            self._log_msg(f"❌ MQTT客户端初始化失败[{type(e).__name__}]：{str(e)}")
            self.mqtt_client = None

    def start_mqtt(self):
        """启动MQTT连接"""
        if self.mqtt_client is None:
            self.init_mqtt_client()
        
        if self.mqtt_client:
            try:
                self.mqtt_client.connect(self.broker, self.port)
                self.mqtt_client.loop_start()
                self._log_msg(f"🔄 开始MQTT后台循环，等待连接...")
            except Exception as e:
                self._log_msg(f"❌ MQTT连接发起失败[{type(e).__name__}]：{str(e)}")
                self._reconnect()
        else:
            self._log_msg(f"❌ MQTT客户端未初始化，无法启动")

    def _on_connect(self, client, userdata, flags, rc):
        """连接回调：详细结果码"""
        rc_msg = {
            0: "连接成功",
            1: "协议版本错误",
            2: "无效的客户端ID",
            3: "服务器不可用",
            4: "用户名/密码错误",
            5: "未授权访问",
            6: "未知错误"
        }
        if rc == 0:
            self.connected = True
            self.reconnect_count = 0
            self._log_msg(f"✅ MQTT连接成功：{rc_msg.get(rc, f'未知结果码{rc}')}")
            self.mqtt_client.subscribe("esp32/data")
            self.mqtt_client.subscribe("esp32/status")
        else:
            self.connected = False
            self._log_msg(f"❌ MQTT连接失败[结果码{rc}]：{rc_msg.get(rc, f'未知结果码{rc}')}")
            self._reconnect()

    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        self.connected = False
        if rc != 0:
            self._log_msg(f"⚠️ MQTT意外断开[结果码{rc}]，准备重连...")
            self._reconnect()
        else:
            self._log_msg(f"ℹ️ MQTT正常断开连接")

    def _on_message(self, client, userdata, msg):
        """消息接收回调"""
        try:
            payload = msg.payload.decode('utf-8')
            self._log_msg(f"📥 收到[{msg.topic}]：{payload}")
            if self.data_callback:
                Clock.schedule_once(lambda dt: self.data_callback(f"📥 {msg.topic}: {payload}"), 0)
        except Exception as e:
            self._log_msg(f"❌ 解析消息失败[{type(e).__name__}]：{str(e)}")

    def publish_command(self, topic, payload):
        """发布指令"""
        if not self.connected:
            self._log_msg(f"❌ 发布失败：MQTT未连接（{topic}：{payload}）")
            return False
        
        try:
            result = self.mqtt_client.publish(topic, payload, qos=1)
            result.wait_for_publish(timeout=5)
            if result.is_published():
                self._log_msg(f"📤 发送成功[{topic}]：{payload}")
                return True
            else:
                self._log_msg(f"❌ 发送超时[{topic}]：{payload}")
                return False
        except Exception as e:
            self._log_msg(f"❌ 发布失败[{type(e).__name__}]：{str(e)}（{topic}：{payload}）")
            return False

    def _reconnect(self):
        """自动重连"""
        if self.reconnect_count < self.max_reconnect_attempts:
            self.reconnect_count += 1
            self._log_msg(f"🔄 第{self.reconnect_count}/{self.max_reconnect_attempts}次重连，5秒后尝试...")
            Clock.schedule_once(lambda dt: self.start_mqtt(), 5)
        else:
            self._log_msg(f"❌ 达到最大重连次数，停止重连")

    def _log_msg(self, msg):
        """统一日志处理（带时间戳）"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_msg = f"[{timestamp}] {msg}"
        print(log_msg)  # 电脑调试用
        if self.data_callback:
            Clock.schedule_once(lambda dt: self.data_callback(log_msg), 0)

    def stop_mqtt(self):
        """停止MQTT"""
        try:
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
                self.connected = False
                self._log_msg(f"ℹ️ MQTT已停止")
        except Exception as e:
            self._log_msg(f"❌ 停止MQTT失败[{type(e).__name__}]：{str(e)}")