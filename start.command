#!/bin/bash

# ── Ewitz Clip Bot Launcher ──
cd "$(dirname "$0")"

echo ""
echo "  ███████╗██╗    ██╗██╗████████╗███████╗"
echo "  ██╔════╝██║    ██║██║╚══██╔══╝╚════██║"
echo "  █████╗  ██║ █╗ ██║██║   ██║       ██╔╝"
echo "  ██╔══╝  ██║███╗██║██║   ██║      ██╔╝ "
echo "  ███████╗╚███╔███╔╝██║   ██║      ██║  "
echo "  ╚══════╝ ╚══╝╚══╝ ╚═╝   ╚═╝      ╚═╝  "
echo ""
echo "  EWITZ CLIP BOT — starting up..."
echo ""

# Kill anything already running on port 5001
lsof -ti :5001 | xargs kill -9 2>/dev/null

# Kill any leftover tunnels
pkill -f ngrok 2>/dev/null
pkill -f cloudflared 2>/dev/null
sleep 1

# Start Flask in background
echo "  [1/2] Starting Flask app..."
python3 app.py > /tmp/ewitz_app.log 2>&1 &
APP_PID=$!
sleep 3

# Check Flask started
if ! lsof -ti :5001 > /dev/null 2>&1; then
  echo "  ERROR: Flask failed to start. Check /tmp/ewitz_app.log"
  read -p "Press Enter to close..."
  exit 1
fi
echo "  ✓ App running"

# Start localhost.run tunnel
echo "  [2/2] Starting share tunnel..."
ssh -o StrictHostKeyChecking=no -R 80:localhost:5001 nokey@localhost.run > /tmp/ewitz_tunnel.log 2>&1 &
NGROK_PID=$!
sleep 8

# Grab the public URL
PUBLIC_URL=$(grep -o 'https://[a-zA-Z0-9]*\.lhr\.life' /tmp/ewitz_tunnel.log | head -1)

echo ""
echo "  ✓ Local: http://localhost:5001"
if [ -n "$PUBLIC_URL" ]; then
  echo "  ✓ Share: $PUBLIC_URL"
fi
echo ""
echo "  Opening in browser..."
open "http://localhost:5001"
echo ""
echo "  Press Ctrl+C to stop everything."
echo ""

# Wait and keep alive
trap "kill $APP_PID $NGROK_PID 2>/dev/null; echo ''; echo '  Ewitz Clip Bot stopped.'; exit 0" INT
wait
