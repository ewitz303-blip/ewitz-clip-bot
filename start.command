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
pkill -f "localhost.run" 2>/dev/null
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

# Start ngrok with permanent domain
echo "  [2/2] Starting ngrok tunnel..."
/opt/homebrew/bin/ngrok http --url=ewitzclipbot.ngrok.app 5001 --log=stdout > /tmp/ewitz_ngrok.log 2>&1 &
NGROK_PID=$!
sleep 5

PUBLIC_URL="https://ewitzclipbot.ngrok.app"

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
