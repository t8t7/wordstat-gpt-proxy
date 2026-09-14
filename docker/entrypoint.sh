#!/bin/sh
set -eu

export DISPLAY=:99

Xvfb :99 -screen 0 1440x1000x24 -nolisten tcp &
sleep 1
x11vnc -display :99 -forever -shared -localhost -nopw -rfbport 5900 >/tmp/x11vnc.log 2>&1 &
websockify --web /usr/share/novnc 7900 localhost:5900 >/tmp/novnc.log 2>&1 &

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --proxy-headers \
    --forwarded-allow-ips 127.0.0.1
