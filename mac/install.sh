#!/usr/bin/env bash
# CloudLap installer for macOS.
#   curl -fsSL https://raw.githubusercontent.com/jaswanthkumarj1234-beep/cloudlap/main/mac/install.sh | bash
set -euo pipefail

RAW="https://raw.githubusercontent.com/jaswanthkumarj1234-beep/cloudlap/main/mac"
APP="$HOME/.cloudlap"
VENV="$APP/venv"
LOGS="$APP/logs"
AGENTS="$HOME/Library/LaunchAgents"
PORT=8787
UID_NUM="$(id -u)"

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
fail() { printf '\n\033[31mError:\033[0m %s\n' "$*" >&2; exit 1; }

# Questions must read from the terminal, because stdin is the downloaded script.
[ -r /dev/tty ] || fail "This installer needs an interactive Terminal window."
ask()  { local a; read -r -p "$1" a </dev/tty; printf '%s' "$a"; }
asks() { local a; read -r -s -p "$1" a </dev/tty; echo >&2; printf '%s' "$a"; }

[ "$(uname)" = "Darwin" ] || fail "This installer is for macOS only."

say "1/6  Checking Python (3.10 or newer)"
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  if command -v "$c" >/dev/null 2>&1; then
    if "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
      PY="$(command -v "$c")"; break
    fi
  fi
done
if [ -z "$PY" ]; then
  fail "Python 3.10 or newer was not found. Install it from https://www.python.org/downloads/macos/ (or run: brew install python), then run this installer again."
fi
echo "Using $PY"

say "2/6  Downloading CloudLap"
mkdir -p "$APP/app" "$LOGS" "$AGENTS"
chmod 700 "$APP"
SRC_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "$(dirname "${BASH_SOURCE[0]}")/server.py" ]; then
  SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
for f in server.py requirements.txt; do
  if [ -n "$SRC_DIR" ]; then cp "$SRC_DIR/$f" "$APP/app/$f"
  else curl -fsSL "$RAW/$f" -o "$APP/app/$f" || fail "Could not download $f. Check your internet connection."; fi
done

say "3/6  Installing Python packages (this can take a minute)"
[ -x "$VENV/bin/python" ] || "$PY" -m venv "$VENV"
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet -r "$APP/app/requirements.txt"

say "4/6  Authenticator lock"
"$VENV/bin/python" "$APP/app/server.py" --setup
echo "Scan the QR code above with Google Authenticator, Microsoft Authenticator, Authy or 1Password."
OK=0
for _ in 1 2 3; do
  CODE="$(ask 'Type the current 6-digit code to confirm it works: ')"
  if "$VENV/bin/python" "$APP/app/server.py" --check "$CODE" >/dev/null 2>&1; then OK=1; break; fi
  echo "That code did not match. Check that your phone clock is set to automatic and try the next code."
done
[ "$OK" = 1 ] || fail "Authenticator not confirmed. Run the installer again to retry."
echo "Authenticator confirmed."

say "5/6  Tunnel (ngrok)"
echo "CloudLap needs a free ngrok account: https://dashboard.ngrok.com/signup"
echo "You need your authtoken (Getting Started > Your Authtoken) and a free static domain (Domains)."
if ! command -v ngrok >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "Installing ngrok with Homebrew..."
    brew install ngrok/ngrok/ngrok || fail "Could not install ngrok. Install it from https://ngrok.com/download and run this installer again."
  else
    fail "ngrok is not installed. Install it from https://ngrok.com/download (or install Homebrew from https://brew.sh and run: brew install ngrok/ngrok/ngrok), then run this installer again."
  fi
fi
NGROK="$(command -v ngrok)"
TOKEN="$(asks 'Paste your ngrok authtoken (hidden, press Enter to skip if already set): ')"
if [ -n "$TOKEN" ]; then "$NGROK" config add-authtoken "$TOKEN" >/dev/null || fail "ngrok rejected the authtoken."; fi
DOMAIN="$(ask 'Your ngrok static domain (for example your-name.ngrok-free.dev): ')"
DOMAIN="${DOMAIN#https://}"; DOMAIN="${DOMAIN%%/*}"
[ -n "$DOMAIN" ] || fail "A static ngrok domain is required."
if "$NGROK" http --help 2>&1 | grep -q -- '--url'; then DOMAIN_FLAG="--url=$DOMAIN"; else DOMAIN_FLAG="--domain=$DOMAIN"; fi

echo
echo "How long should each unlock last?"
echo "  Shorter is safer. The server locks again after this time."
M="$(ask 'Minutes (10, 20, 30 or 60) [10]: ')"
case "$M" in 10|20|30|60) UNLOCK_MIN="$M" ;; *) UNLOCK_MIN=10 ;; esac

say "6/6  Starting CloudLap and setting it to run at login"
cat > "$AGENTS/com.cloudlap.server.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.cloudlap.server</string>
  <key>ProgramArguments</key><array>
    <string>$VENV/bin/python</string><string>$APP/app/server.py</string>
  </array>
  <key>EnvironmentVariables</key><dict>
    <key>CLOUDLAP_PORT</key><string>$PORT</string>
    <key>CLOUDLAP_UNLOCK_MINUTES</key><string>$UNLOCK_MIN</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$LOGS/server.log</string>
  <key>StandardErrorPath</key><string>$LOGS/server.err.log</string>
</dict></plist>
EOF
cat > "$AGENTS/com.cloudlap.tunnel.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.cloudlap.tunnel</string>
  <key>ProgramArguments</key><array>
    <string>$NGROK</string><string>http</string><string>$DOMAIN_FLAG</string>
    <string>--host-header=rewrite</string><string>--log=stdout</string><string>$PORT</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$LOGS/tunnel.log</string>
  <key>StandardErrorPath</key><string>$LOGS/tunnel.err.log</string>
</dict></plist>
EOF
for n in server tunnel; do
  launchctl bootout "gui/$UID_NUM/com.cloudlap.$n" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$UID_NUM" "$AGENTS/com.cloudlap.$n.plist" || fail "Could not start the $n service. See $LOGS."
done

sleep 4
if curl -fsS -o /dev/null -m 5 -X POST "http://127.0.0.1:$PORT/mcp" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d '{}' 2>/dev/null \
   || curl -sS -o /dev/null -m 5 "http://127.0.0.1:$PORT/mcp" 2>/dev/null; then
  echo "The server is running."
else
  echo "The server did not answer yet. Check $LOGS/server.err.log"
fi

say "Done. Last step: connect Claude"
echo "1. In Claude open Settings > Connectors > Add custom connector."
echo "2. Paste this address (keep it private):"
echo
echo "     https://$DOMAIN/mcp"
echo
echo "3. To use it, tell Claude: Connect to CloudLap, code is 123456   (use the real code from your authenticator app)"
echo
echo "Unlock lasts $UNLOCK_MIN minutes. Say 'lock CloudLap' when you finish."
echo "If your Mac sleeps, CloudLap is unreachable. See the Keeping your Mac awake section in SETUP-MAC.md."
echo "To remove CloudLap later: curl -fsSL $RAW/uninstall.sh | bash"
