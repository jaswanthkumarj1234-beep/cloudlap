# CloudLap Setup Guide (Windows)

This guide takes you from a fresh laptop to a working, locked-down CloudLap in about 15 minutes.
You do not need Claude to install or run the server. You need Claude only to *use* it, because
Claude is the client that connects to your laptop.

## What you need

- Windows 10 or 11
- Python 3.10 or later ([python.org/downloads](https://python.org/downloads); tick **Add Python to PATH**)
- Git ([git-scm.com](https://git-scm.com/downloads)) or use **Code > Download ZIP** on GitHub
- A free ngrok account ([ngrok.com](https://ngrok.com))
- An authenticator app on your phone (Google Authenticator, Microsoft Authenticator, Authy, 1Password and so on)
- A Claude account whose plan supports custom connectors. Check Settings > Connectors in Claude to confirm.

## Step 1. Download

```
git clone https://github.com/jaswanthkumarj1234-beep/cloudlap.git
cd cloudlap
```

## Step 2. Install

Double-click `setup.bat`, or run it in a terminal. It checks Python, installs the requirements,
installs ngrok through winget if missing, and creates `config.json` from the template.

## Step 3. Set up the authenticator lock (do not skip)

> **Warning:** If you skip this step, the server has NO authentication and anyone who learns your
> tunnel URL can run commands on your computer. Do this before you start the server or add the connector.

```
pip install qrcode pillow
python totp_setup.py --show-qr
```

1. A window shows a QR code. Scan it with your authenticator app. Name the entry "CloudLap".
2. Test it: type the current 6-digit code into
   `python totp_setup.py --check 123456`. It should say the code is valid.
3. Close the QR window. The secret is stored in `config.json`, which Git ignores. Never commit or share it.

To replace the secret later, run `python totp_setup.py --new --show-qr`. The old entry in the app stops working.

## Step 4. Set up ngrok (one time)

1. In the ngrok dashboard, copy your authtoken and run `ngrok config add-authtoken YOUR_TOKEN`.
2. In the dashboard, open **Domains** and create a free static domain, for example `your-name.ngrok-free.dev`.
3. Put that domain in `config.json`: `"ngrok_domain": "your-name.ngrok-free.dev"`.

## Step 5. Start the server

Run `start.bat` (console) or `launcher.pyw` (window). Leave it running.

Optional: `watchdog.ps1` restarts the server and tunnel if they stop. To run it at login, put a shortcut
that starts it hidden in `shell:startup`.

## Step 6. Connect Claude

1. In Claude, open **Settings > Connectors > Add custom connector**.
2. Paste `https://your-name.ngrok-free.dev/mcp`.
3. Treat that URL as private. Do not post it or screenshot it.

## Step 7. Unlock each session

With the lock on, every tool except `get_system_info` refuses to run until you unlock.

1. Open your authenticator app and read the current 6-digit code.
2. Tell Claude: "Connect to CloudLap, code is 123456". Claude calls the `unlock` tool.
3. The unlock lasts `unlock_minutes` (default 10) and ends sooner if the server restarts.
   Each code works once. After `max_unlock_failures` wrong codes (default 3) the server pauses unlock attempts.

Say "lock CloudLap" when you finish, and Claude calls the `lock` tool.

## Settings you can change in config.json

| Key | Default | Meaning |
|-----|---------|---------|
| `unlock_minutes` | 10 | How long one unlock lasts. Longer is more convenient and less safe. |
| `max_unlock_failures` | 3 | Wrong codes allowed before unlock attempts are paused. |
| `allowed_directories` | `["~"]` | Folders the file tools may touch. Narrow this if you can. |
| `port` | 8787 | Local port. |
| `ngrok_domain` | empty | Your static ngrok domain. |

Restart the server after editing `config.json`. A restart also locks it again.

## Keeping the laptop awake

If the laptop sleeps, CloudLap is unreachable. On a laptop, closing the lid usually triggers sleep.
Either leave the lid open, or in Control Panel > Power Options > *Choose what closing the lid does*,
set it to **Do nothing**. Also set sleep to **Never** while plugged in.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Code rejected | Check the phone's clock is set to automatic. Wait for the next code and try again. |
| "Locked" message from every tool | Normal. Unlock with a fresh code. |
| Claude cannot reach the server | Check the server window, the ngrok window, and that the laptop is awake. |
| HTTP 421 from the tunnel | Do not change the bind address to `127.0.0.1` alone. See `docs/KNOWN_LIMITATIONS.md`. |
| Lost the authenticator | Edit `config.json`, delete `totp_secret`, restart, then run Step 3 again. |

## Safety notes

- Anyone with both your URL and a valid code can run commands on your computer. Keep both private.
- The server still listens on all network interfaces (`0.0.0.0`). Block port 8787 from your local network
  with a Windows Firewall rule if you share your Wi-Fi with others.
- Review `docs/KNOWN_LIMITATIONS.md` and `SECURITY.md` before using this on a computer with sensitive data.
