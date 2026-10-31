#!/usr/bin/env bash
# Executed by bash as a single script, not by emulator-runner's /bin/sh line interpreter.
set -euo pipefail
mkdir -p screenshots
capture_diagnostics() {
  status=$?
  adb logcat -d > screenshots/full-logcat.txt 2>&1 || true
  adb logcat -b crash -d > screenshots/crash-log.txt 2>&1 || true
  adb shell dumpsys activity activities > screenshots/activity-state.txt 2>&1 || true
  adb exec-out screencap -p > screenshots/last-visible-screen.png 2>/dev/null || true
  echo "Runtime validation exit code: ${status}" > screenshots/runtime-exit-status.txt
}
trap capture_diagnostics EXIT

wait_for_log() {
  tag="$1"; pattern="$2"; seconds="$3"
  seen_running=0
  for ((i=0;i<seconds;i+=3)); do
    if adb logcat -d -s "${tag}:I" | grep -E "${pattern}"; then return 0; fi
    if adb shell pidof -s com.openlocal.office | grep -Eq '[0-9]+'; then
      seen_running=1
    elif ((seen_running == 1)); then
      echo "App process exited after launch while awaiting ${pattern}"
      return 1
    elif ((i >= 45)); then
      echo "App never started after 45 seconds while awaiting ${pattern}"
      return 1
    fi
    sleep 3
  done
  echo "Timed out awaiting ${tag}: ${pattern}"
  adb logcat -d -s "${tag}:V" | tail -60 || true
  return 1
}

adb install -r openlocaloffice-build/project/app/build/outputs/apk/release/app-release-signed.apk
adb logcat -c
adb shell am start -n com.openlocal.office/.MainActivity
wait_for_log FG_READER_UI 'LIBRARY_READY' 90
adb exec-out screencap -p > screenshots/fg-reader-home.png
test -s screenshots/fg-reader-home.png

# Native Android EPUB2/EPUB3 parser fixture, >80 MiB with external OPF DTD.
python3 openlocaloffice-build/hotfixes/create-large-epub-fixture.py /tmp/fg-large-book.epub
adb shell run-as com.openlocal.office mkdir -p files
adb exec-in run-as com.openlocal.office sh -c 'cat > files/fg-large-book.epub' < /tmp/fg-large-book.epub
adb shell am start -n com.openlocal.office/.MainActivity -a android.intent.action.VIEW -t application/epub+zip -d file:///data/user/0/com.openlocal.office/files/fg-large-book.epub
wait_for_log FG_BOOK 'EPUB_READY chapters=[1-9][0-9]* illustrations=[0-9]+' 120
adb exec-out screencap -p > screenshots/fg-86mib-epub.png
adb shell input keyevent KEYCODE_BACK
wait_for_log FG_READER_UI 'BACK_TO_LIBRARY' 45
adb shell pidof -s com.openlocal.office | grep -Eq '[0-9]+'

# The real page must decode, not just index archive filenames.
python3 openlocaloffice-build/hotfixes/create-image-zip-fixture.py /tmp/fg-102-images.zip
adb exec-in run-as com.openlocal.office sh -c 'cat > files/fg-102-images.zip' < /tmp/fg-102-images.zip
adb shell am start -n com.openlocal.office/.MainActivity -a android.intent.action.VIEW -t application/zip -d file:///data/user/0/com.openlocal.office/files/fg-102-images.zip
wait_for_log FG_ARCHIVE 'ZIP_READY count=102 comic=true elapsed_ms=[0-9]+' 120
wait_for_log FG_READER_UI 'COMIC_IMAGE_LOADED' 90
adb exec-out screencap -p > screenshots/fg-102-image-zip.png
test -s screenshots/fg-102-image-zip.png
adb logcat -d -s FG_BOOK:I > screenshots/epub-native-parser.txt
adb logcat -d -s FG_ARCHIVE:I > screenshots/archive-index-benchmark.txt
adb logcat -d -s FG_READER_UI:I > screenshots/reader-ui-events.txt
if adb logcat -b crash -d | grep -q 'FATAL EXCEPTION'; then
  echo 'Fatal Android exception during runtime smoke test'
  exit 1
fi
rm -f /tmp/fg-large-book.epub /tmp/fg-102-images.zip
