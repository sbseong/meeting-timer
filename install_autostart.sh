#!/bin/zsh
# 로그인할 때 자동으로 켜지게 등록한다. 해제: ./install_autostart.sh remove
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST="$HOME/Library/LaunchAgents/local.meeting-timer.plist"
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
if [[ "$1" == "remove" ]]; then rm -f "$PLIST"; echo "자동 실행 해제"; exit 0; fi
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>local.meeting-timer</string>
  <key>ProgramArguments</key><array><string>$DIR/run.sh</string></array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
  <key>StandardErrorPath</key><string>$DIR/meeting_timer.log</string>
  <key>StandardOutPath</key><string>$DIR/meeting_timer.log</string>
</dict></plist>
PL
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "자동 실행 등록 완료: $PLIST"
