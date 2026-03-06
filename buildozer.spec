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
android.sdk_path = /home/runner/.buildozer/android/platform/android-sdk
android.ndk_path = /home/runner/.buildozer/android/platform/android-ndk-r25b
android.ndk_version = 25b

[buildozer]
log_level = 2
