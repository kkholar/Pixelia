[app]
title = Pixel Editor
package.name = pixeleditor
package.domain = org.pixeleditor
source.dir = .
source.include_exts = py,png,jpg,jpeg,ttf,txt
version = 1.2

# Pygame yerine kivy ve pygame-sdl2 kullanmanızı öneririm
requirements = python3, pygame-sdl2, sdl2, sdl2_image, sdl2_mixer, sdl2_ttf

orientation = portrait
fullscreen = 1

# İzinler
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# Android API seviyeleri
android.api = 33
android.minapi = 21
android.archs = arm64-v8a

# SDK ve NDK yolları (GitHub Actions için dinamik yapalım)
android.sdk_path = $(ANDROID_HOME)
android.ndk_path = $(ANDROID_NDK_HOME)
android.ndk_version = 25c  # 25b yerine 25c kullanın

# Ek Android ayarları
android.accept_sdk_license = True
android.gradle_dependencies = 'org.libsdl.app:SDL:1.0.0'

# Java ve build araçları
android.java_path = /usr/lib/jvm/java-17-openjdk-amd64
android.bootstrap = sdl2

# P4A ayarları
p4a.branch = develop
p4a.local_recipes = 
p4a.hook = 

# Görsel öğeler
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/splash.png

# Geliştirme ayarları
warn_on_root = 1
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1

# Çözüm önerileri:
# 1. Eğer pygame kullanmak zorundaysanız, 'pygame' yerine 'pygame==2.0.1' yazın
# 2. 'requirements = python3, pygame, numpy, android' şeklinde android paketini ekleyin
# 3. 'android.add_src = java' ile Java kaynak dosyalarını ekleyin
