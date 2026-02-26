app
title = Esp32MobileApp
package.name = esp32app
package.domain = org.esp32
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,pem
source.exclude_exts = spec
source.exclude_dirs = venv,__pycache__,build
version = 0.0.1
orientation = portrait

# 核心：强制生成APK（关闭AAB）
android.aab = False
# 核心：指定Python版本匹配workflow
android.blacklist_libs = libpython3.9.so
# 核心：补充关键依赖
requirements = python3,kivy==2.2.1,kivymd==1.2.0,paho-mqtt,pyjnius,setuptools

entrypoint = main.py
android.arch = arm64-v8a,armeabi-v7a
android.add_assets = ca.pem

# 修复NDK/Gradle冲突（适配python-for-android）
android.accept_sdk_license = True
android.api = 31          # 降级API，避免兼容问题
android.minapi = 21
android.ndk = 24b         # 匹配API 31的NDK版本
android.ndk_api = 21
android.sdk = 31
android.gradle_download = https://services.gradle.org/distributions/gradle-7.4.2-all.zip
android.gradle_plugin = 7.2.0
p4a.bootstrap = sdl2
p4a.gradle_options = -Dorg.gradle.java.home=/usr/lib/jvm/java-17-openjdk-amd64
android.permissions = INTERNET, ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE

[buildozer]
log_level = 2
warn_on_root = 1
# 核心：强制Buildozer使用稳定的python-for-android版本
p4a.source = git+https://github.com/kivy/python-for-android.git@v2023.07.05
