"""CloudLap guided setup.

Run once:  python setup_wizard.py   (setup.bat does this for you)

It installs the requirements, sets up the authenticator lock, configures ngrok,
and starts CloudLap. Safe to run again: it keeps what is already configured.
"""

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

TOTAL = 7


def step(n: int, title: str) -> None:
    print(f"\n[{n}/{TOTAL}] {title}")
    print("-" * 60)


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        value = ""
    return value or default


def yes(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    answer = ask(f"{prompt} ({hint})").lower()
    if not answer:
        return default
    return answer.startswith("y")


def fail(msg: str) -> None:
    print(f"\nCannot continue: {msg}")
    input("Press Enter to close.")
    sys.exit(1)


def run(cmd: list, quiet: bool = True) -> int:
    kw = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL} if quiet else {}
    return subprocess.call(cmd, cwd=ROOT, **kw)


def find_ngrok() -> str:
    found = shutil.which("ngrok")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = [Path(local) / "Microsoft" / "WinGet" / "Links" / "ngrok.exe"]
    pkgs = Path(local) / "Microsoft" / "WinGet" / "Packages"
    if pkgs.exists():
        candidates += list(pkgs.glob("ngrok*/ngrok.exe"))
    for c in candidates:
        if c.exists():
            return str(c)
    return ""


def main() -> None:
    print("=" * 60)
    print("  CloudLap setup")
    print("  About 5 minutes. You will need your phone (authenticator app)")
    print("  and a free ngrok account: https://ngrok.com")
    print("=" * 60)

    # 1. Python
    step(1, "Checking Python")
    if sys.version_info < (3, 10):
        fail("Python 3.10 or newer is required. Install it from python.org and tick 'Add Python to PATH'.")
    print(f"Python {sys.version.split()[0]} OK")

    # 2. Requirements
    step(2, "Installing requirements (this can take a minute)")
    code = run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "qrcode", "pillow"])
    if code != 0:
        fail("pip could not install the requirements. Check your internet connection and try again.")
    print("Requirements installed")

    import totp
    import totp_setup

    cfg = totp_setup.load_config()
    if not cfg:
        example = ROOT / "config.example.json"
        if example.exists():
            shutil.copy(example, ROOT / "config.json")
            cfg = totp_setup.load_config()
            print("Created config.json")

    # 3. Authenticator lock
    step(3, "Authenticator lock (protects your computer)")
    print("Without this, anyone who learns your tunnel URL can control your computer.")
    secret = cfg.get("totp_secret", "")
    if secret and yes("An authenticator is already set up. Keep it?", True):
        print("Keeping the existing authenticator")
    else:
        secret = totp_setup.ensure_secret(force_new=True)
        print("\nA window will show a QR code. Scan it with Google Authenticator, Microsoft")
        print("Authenticator, Authy or similar. Close the window when you have scanned it.")
        input("Press Enter to show the QR code...")
        try:
            totp_setup.show_qr(secret)
        except Exception as exc:  # no display, tkinter missing, and so on
            print(f"\nCould not show the QR window ({exc}).")
            print("Add it by hand in your authenticator app, choose 'enter a setup key':")
            print(f"  Key: {secret}")
            print("Keep this key private. It is also saved in config.json.")
        verified = False
        for _ in range(5):
            entered = ask("Type the 6-digit code now shown in your app").replace(" ", "")
            if totp.verify(secret, entered) is not None:
                verified = True
                print("Code accepted")
                break
            print("That code did not match. Wait for the next code and try again.")
        if not verified:
            print("\nWARNING: the code was never confirmed. You may not be able to unlock CloudLap.")
            print("Run  python totp_setup.py --new --show-qr  to start over.")
    cfg = totp_setup.load_config()

    # 4. ngrok
    step(4, "ngrok tunnel (lets Claude reach your computer)")
    ngrok = find_ngrok()
    if not ngrok:
        print("ngrok is not installed. Trying to install it with winget...")
        run(["winget", "install", "ngrok.ngrok", "--accept-package-agreements", "--accept-source-agreements", "--silent"])
        ngrok = find_ngrok()
    if not ngrok:
        fail("ngrok is not installed. Install it from https://ngrok.com/download, then run setup again.")
    print("ngrok found")
    print("\n1. Sign in at https://dashboard.ngrok.com and copy your authtoken (Your Authtoken page).")
    print("2. Open Domains, create your free static domain, and copy it (looks like name.ngrok-free.dev).")
    print("\nNote: a free ngrok domain can only be used by ONE computer at a time. If CloudLap already")
    print("runs on another computer, use a separate ngrok account (a different email) for this one,")
    print("or stop the other computer first.")
    token = ask("\nPaste your ngrok authtoken (or press Enter if you already added it)")
    if token:
        if run([ngrok, "config", "add-authtoken", token]) != 0:
            print("ngrok did not accept that token. You can add it later with: ngrok config add-authtoken TOKEN")
    current_domain = cfg.get("ngrok_domain", "")
    domain = ask("Paste your static domain", current_domain)
    domain = domain.replace("https://", "").replace("http://", "").strip("/ ")
    if not domain or "." not in domain:
        fail("A valid ngrok static domain is needed, for example name.ngrok-free.dev.")
    cfg["ngrok_domain"] = domain

    # 5. Access
    step(5, "What can Claude touch?")
    print("By default Claude may use files anywhere in your user folder.")
    dirs = ask("Limit to specific folders? Enter paths separated by ';' or press Enter for the default", "")
    if dirs:
        cfg["allowed_directories"] = [d.strip() for d in dirs.split(";") if d.strip()]
    minutes = ask("How many minutes should one unlock last? (shorter is safer)", str(cfg.get("unlock_minutes", 10)))
    try:
        cfg["unlock_minutes"] = max(1, int(minutes))
    except ValueError:
        cfg["unlock_minutes"] = 10
    totp_setup.save_config(cfg)
    print("Settings saved to config.json")

    # 6. Auto start and run
    step(6, "Starting CloudLap")
    watchdog = ROOT / "watchdog.ps1"
    autostart = False
    if watchdog.exists():
        autostart = yes("Start CloudLap automatically when you sign in to Windows?", True)
    if autostart:
        startup = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        startup.mkdir(parents=True, exist_ok=True)
        vbs = startup / "CloudLap Watchdog.vbs"
        vbs.write_text(
            "' Starts CloudLap at login. Delete this file to turn auto-start off.\n"
            'CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -WindowStyle Hidden '
            f'-ExecutionPolicy Bypass -File ""{watchdog}""", 0, False\n',
            encoding="utf-8",
        )
        print("Auto-start installed")
        flags = 0x08000000 | 0x00000008  # no window, detached
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-File", str(watchdog)],
            cwd=ROOT, creationflags=flags,
        )
        print("Started in the background")
    else:
        print("Skipping auto-start. Start CloudLap yourself with start.bat when you need it.")

    # 7. Check
    step(7, "Checking")
    port = int(cfg.get("port", 8787))
    up = False
    if autostart:
        for _ in range(20):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=1):
                    up = True
                    break
            except OSError:
                time.sleep(1)
        print("Server is running" if up else "Server did not answer yet. See watchdog.log in this folder.")

    print("\n" + "=" * 60)
    print("  Almost done. One last step, in Claude:")
    print("=" * 60)
    print("  1. Open Settings > Connectors > Add custom connector")
    print(f"  2. Paste this address:  https://{domain}/mcp")
    print("  3. Keep that address private.")
    print("  4. To use it, open your authenticator app and tell Claude:")
    print('       "Connect to CloudLap, code is 123456"  (use the real code)')
    print()
    print("  Tip: if the laptop sleeps or the lid closes, CloudLap goes offline.")
    print("  Control Panel > Power Options > 'Choose what closing the lid does'.")
    print()
    input("Press Enter to close.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup cancelled. Run it again any time.")
