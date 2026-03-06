buildozer.spec:
[app]
title = Pixel Editor
package.name = pixeleditor
package.domain = org.pixeleditor
source.dir = .
source.include_exts = py
version = 1.2
requirements = python3,pygame
orientation = portrait
fullscreen = 1
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.archs = arm64-v8a
android.sdk_path = /usr/local/lib/android/sdk
android.ndk_path = /usr/local/lib/android/sdk/ndk/23.2.8568313
android.ndk_version = 23.2.8568313
android.build_tools_version = 34.0.0

[buildozer]
log_level = 2
