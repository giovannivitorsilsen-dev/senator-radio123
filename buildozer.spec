[app]
title = Unfollow
package.name = unfollow
package.domain = app.unfollow.prototype
source.dir = .
source.include_exts = py,kv
source.exclude_dirs = tests,.git,.github,bin,.buildozer
version = 0.3.0
requirements = python3,kivy,pillow,requests,urllib3,idna,certifi,charset-normalizer,pysocks,pydantic==1.10.19,instagrapi==1.19.8
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.accept_sdk_license = True
android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
[buildozer]
log_level = 2
warn_on_root = 1
