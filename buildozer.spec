- name: Manual p4a build (alternative)
  run: |
    # Buildozer yerine direkt p4a kullan
    pip install python-for-android
    
    p4a apk \
      --private . \
      --package=org.pixeleditor.pixeleditor \
      --name "Pixel Editor" \
      --version 1.2 \
      --bootstrap=sdl2 \
      --requirements=python3,pygame==2.0.1 \
      --arch=arm64-v8a \
      --sdk-dir /home/runner/.buildozer/android/platform/android-sdk \
      --ndk-dir /home/runner/.buildozer/android/platform/android-ndk-r25c \
      --ndk-version=25c \
      --android-api=33 \
      --minsdk=21 \
      --permission=WRITE_EXTERNAL_STORAGE \
      --permission=READ_EXTERNAL_STORAGE \
      --debug
