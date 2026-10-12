# CloudLap Setup Guide (macOS)

This takes a Mac from nothing to a working, locked-down CloudLap in about 10 minutes.
You do not need Claude to install or run the server. You need Claude only to *use* it.

## Quick start

1. Open **Terminal** (press Cmd+Space, type Terminal, press Enter).
2. Paste this one line and press Enter:

```
curl -fsSL https://raw.githubusercontent.com/jaswanthkumarj1234-beep/cloudlap/main/mac/install.sh | bash
```

3. Answer the questions. The installer:
   - checks for Python 3.10 or newer,
   - installs CloudLap into a hidden folder, `~/.cloudlap`,
   - shows a QR code for your authenticator app and checks the code you type,
   - installs ngrok (with Homebrew) and asks for your authtoken and free static domain,
   - asks how long each unlock lasts (10, 20, 30 or 60 minutes),
   - starts CloudLap and makes it start again at login.
4. At the end it prints an address. In Claude go to **Settings > Connectors > Add custom connector** and paste it. Keep that address private.
5. To use it, tell Claude: "Connect to CloudLap, code is 123456" (use the real code from your authenticator app).

Have these ready: an iPhone or Android phone with an authenticator app (Google or Microsoft Authenticator, Authy, 1Password),
and a free [ngrok](https://ngrok.com) account.

### If Python is missing

Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/macos/), or with Homebrew: `brew install python`.
Then run the one-line command again.

### If ngrok is missing and you do not use Homebrew

Install ngrok from [ngrok.com/download](https://ngrok.com/download), or install Homebrew from [brew.sh](https://brew.sh),
then run the one-line command again.

## Using it each time

With the lock on, every tool except `get_system_info` refuses to run until you unlock.

1. Read the current 6-digit code in your authenticator app.
2. Tell Claude: "Connect to CloudLap, code is 123456".
3. The unlock lasts the time you chose, and ends sooner if the server restarts. Each code works once.
   After 3 wrong codes, unlock attempts pause for 5 minutes.

Say "lock CloudLap" when you finish.

## Keeping your Mac awake

If your Mac sleeps, CloudLap is unreachable. Choose one:

- **Plugged in, lid open:** System Settings > Battery (or Energy) > turn on *Prevent automatic sleeping on power adapter when the display is off*.
- **Lid closed:** macOS sleeps when the lid closes unless an external display is connected. Keep the lid open, or use a free app such as Amphetamine.

## Where things are

| What | Where |
|------|-------|
| Server, Python packages | `~/.cloudlap/app`, `~/.cloudlap/venv` |
| Authenticator secret | `~/.cloudlap/totp_secret.txt` (private, never share) |
| Saved contexts and notes | `~/.cloudlap/contexts`, `~/.cloudlap/memory.md` |
| Activity log (every tool call) | `~/.cloudlap/audit_log.jsonl` |
| Service logs | `~/.cloudlap/logs` |
| Login services | `~/Library/LaunchAgents/com.cloudlap.server.plist` and `com.cloudlap.tunnel.plist` |

## Change the unlock time

Run the installer again and choose a different time. It keeps your authenticator secret if one already exists.

## Update

Run the one-line command again. Your secret, saved contexts and notes stay.

## Uninstall

```
curl -fsSL https://raw.githubusercontent.com/jaswanthkumarj1234-beep/cloudlap/main/mac/uninstall.sh | bash
```

It stops the services and asks before deleting `~/.cloudlap`. Afterwards delete the CloudLap entry in your authenticator app
and the connector in Claude.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Code rejected | Set your phone's clock to automatic. Wait for the next code and try again. |
| "Locked" message from every tool | Normal. Unlock with a fresh code. |
| Claude cannot reach the server | Check the Mac is awake and online. Look at `~/.cloudlap/logs/server.err.log` and `tunnel.err.log`. |
| ngrok says the domain is in use | A free ngrok domain works on one computer at a time. Stop the other tunnel or use another ngrok account. |
| Restart the services | `launchctl kickstart -k gui/$(id -u)/com.cloudlap.server` (and `com.cloudlap.tunnel`) |
| Lost the authenticator | Delete `~/.cloudlap/totp_secret.txt`, then run the installer again. |

## Safety notes

- Anyone with both your address and a valid code can run commands on your Mac. Keep both private.
- The Mac server listens on `127.0.0.1` only, so other devices on your Wi-Fi cannot reach it directly.
- The command filter is a simple guard, not a sandbox. Do not use CloudLap on a Mac holding data you cannot afford to lose without a backup.
- The Mac version does not yet have the Windows version's folder restrictions or rate limit. See [SECURITY.md](SECURITY.md).
