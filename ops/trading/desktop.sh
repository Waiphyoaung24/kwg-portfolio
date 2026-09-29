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
if [ -n "${MT5_DEMO_LOGIN:-}" ]; then
  [[ "$MT5_DEMO_LOGIN" =~ ^[0-9]+$ ]] || { echo "Invalid MT5_DEMO_LOGIN" >&2; exit 1; }
  server_offset="${MT5_SERVER_OFFSET_SECONDS:-0}"
  case "$server_offset" in 0|7200|10800) ;; *) echo "Invalid MT5_SERVER_OFFSET_SECONDS" >&2; exit 1;; esac
  (
    while true; do
      if [ -f "$terminal" ]; then
        script -q -e -c "wine /opt/python/python.exe /opt/trading/observe-gold.py --login $MT5_DEMO_LOGIN --state 'C:\users\mt5\gold-observer.sqlite3' --server-offset-seconds $server_offset" /dev/null || true
      fi
      sleep 10
    done
  ) &
  # Reconcile an existing one-shot journal after terminal startup; resume cannot enter.
  (
    sleep 10
    for attempt in {1..30}; do
      if script -q -e -c "wine /opt/python/python.exe /opt/trading/demo_one_shot.py resume --state 'C:\users\mt5\gold-one-shot.sqlite3'" /dev/null; then
        if [ -n "${TRADING_CONTROL_SECRET:-}" ]; then
          python3 /opt/trading/control_server.py
        fi
        break
      fi
      sleep 10
    done
  ) &
fi
# The installer may exit normally after launching MT5; keep the desktop available.
wait
