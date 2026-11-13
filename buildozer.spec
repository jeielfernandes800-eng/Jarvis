[app]
title = Jarvis
package.name = jarvis
package.domain = org.jarvis
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json
version = 0.1
requirements = python3,kivy==2.3.0,requests,certifi,urllib3,idna,charset-normalizer,pyjnius,plyer,android
orientation = portrait
fullscreen = 0
android.permissions = RECORD_AUDIO,INTERNET,FOREGROUND_SERVICE,POST_NOTIFICATIONS
android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
