#!/usr/bin/env bash
set -euo pipefail
umask 077
trap 'kill $(jobs -pr) 2>/dev/null || true' EXIT
trap 'exit 0' TERM INT
Xvfb "$DISPLAY" -screen 0 1280x800x24 -nolisten tcp &
for attempt in {1..50}; do
  if xdpyinfo >/dev/null 2>&1; then break; fi
  sleep 0.1
done
xdpyinfo >/dev/null
openbox &
# VNC is internal only; noVNC is published only on the host's SSH-protected loopback.
x11vnc -display "$DISPLAY" -localhost -rfbport 5900 -forever -shared -nopw &
websockify --web /usr/share/novnc 6080 localhost:5900 &
terminal="$WINEPREFIX/drive_c/Program Files/MetaTrader 5/terminal64.exe"
if [ -f "$terminal" ]; then
  wine "$terminal" &
else
  # Interactive installer: the owner reviews terms and enters the demo login.
  wine /opt/trading/mt5setup.exe &
fi
# The installer may exit normally after launching MT5; keep the desktop available.
wait
