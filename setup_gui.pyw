"""CloudLap setup - a plain window, no terminal, no typing commands.

Double-click "Start CloudLap.bat". This window walks through 5 short steps:
install, authenticator, ngrok, options, finish. Safe to run again.
Uses only the Python standard library until the install step finishes.
"""

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

BG, CARD, ACCENT, TEXT, MUTED = "#0f172a", "#1e293b", "#6366f1", "#f1f5f9", "#94a3b8"
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


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


def run(cmd: list) -> int:
    return subprocess.call(cmd, cwd=ROOT, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)


class Wizard(tk.Tk):
    STEPS = ["Install", "Authenticator", "ngrok", "Options", "Finish"]

    def __init__(self):
        super().__init__()
        self.title("CloudLap setup")
        self.configure(bg=BG)
        self.geometry("560x640")
        self.minsize(520, 600)
        self.cfg = {}
        self.totp = None
        self.totp_setup = None
        self.secret = ""
        self.qr_photo = None
        self.ngrok_path = ""
        self.autostart = tk.BooleanVar(value=True)
        self.minutes = tk.StringVar(value="60")
        self.step = 0

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Horizontal.TProgressbar", troughcolor=CARD, background=ACCENT, bordercolor=CARD)

        self.head = tk.Label(self, text="", bg=BG, fg=MUTED, font=("Segoe UI", 10))
        self.head.pack(anchor="w", padx=24, pady=(18, 0))
        self.title_lbl = tk.Label(self, text="", bg=BG, fg=TEXT, font=("Segoe UI", 18, "bold"))
        self.title_lbl.pack(anchor="w", padx=24, pady=(2, 8))
        self.body = tk.Frame(self, bg=CARD)
        self.body.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        self.foot = tk.Frame(self, bg=BG)
        self.foot.pack(fill="x", padx=24, pady=(0, 18))
        self.next_btn = tk.Button(self.foot, text="Next", bg=ACCENT, fg="white", relief="flat",
                                  font=("Segoe UI", 11, "bold"), padx=22, pady=8, command=self.go_next)
        self.next_btn.pack(side="right")
        self.show_step()

    # ---------- helpers ----------
    def clear(self):
        for w in self.body.winfo_children():
            w.destroy()

    def label(self, text, size=11, color=TEXT, bold=False, pad=(0, 8)):
        lbl = tk.Label(self.body, text=text, bg=CARD, fg=color, justify="left", wraplength=470,
                       font=("Segoe UI", size, "bold" if bold else "normal"))
        lbl.pack(anchor="w", padx=18, pady=pad)
        return lbl

    def link(self, text, url):
        b = tk.Button(self.body, text=text, bg=BG, fg=TEXT, relief="flat", padx=12, pady=6,
                      font=("Segoe UI", 10), command=lambda: webbrowser.open(url))
        b.pack(anchor="w", padx=18, pady=3)

    def entry(self, var, width=46):
        e = tk.Entry(self.body, textvariable=var, width=width, font=("Segoe UI", 11),
                     bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat")
        e.pack(anchor="w", padx=18, pady=(2, 4), ipady=6)
        return e

    def paste_button(self, var):
        def paste():
            try:
                var.set(self.clipboard_get().strip())
            except tk.TclError:
                pass
        tk.Button(self.body, text="Paste from clipboard", bg=BG, fg=MUTED, relief="flat",
                  font=("Segoe UI", 9), command=paste).pack(anchor="w", padx=18, pady=(0, 6))

    def show_step(self):
        self.clear()
        self.head.config(text=f"Step {self.step + 1} of {len(self.STEPS)}")
        self.title_lbl.config(text=self.STEPS[self.step])
        self.next_btn.config(state="normal", text="Next")
        getattr(self, f"page_{self.step}")()

    def go_next(self):
        ok = getattr(self, f"leave_{self.step}", lambda: True)()
        if not ok:
            return
        if self.step == len(self.STEPS) - 1:
            self.destroy()
            return
        self.step += 1
        self.show_step()

    # ---------- step 1: install ----------
    def page_0(self):
        if sys.version_info < (3, 10):
            self.label("Python 3.10 or newer is needed. Please install it from python.org "
                       "(tick 'Add Python to PATH') and open this again.", color="#f87171")
            self.next_btn.config(state="disabled")
            return
        self.label("CloudLap lets Claude reach your computer safely. This takes about 5 minutes.\n\n"
                   "You will need:\n  - your phone (for an authenticator app)\n"
                   "  - a free ngrok account (ngrok.com)", pad=(14, 8))
        self.status = self.label("Getting things ready...", color=MUTED)
        self.bar = ttk.Progressbar(self.body, mode="indeterminate", length=440)
        self.bar.pack(padx=18, pady=8)
        self.bar.start(12)
        self.next_btn.config(state="disabled")
        threading.Thread(target=self.install, daemon=True).start()

    def install(self):
        code = run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "qrcode", "pillow"])
        self.after(0, self.install_done, code)

    def install_done(self, code):
        self.bar.stop()
        if code != 0:
            self.status.config(text="Could not install the needed parts. Check your internet "
                                    "connection, then close this window and open it again.", fg="#f87171")
            return
        import totp
        import totp_setup
        self.totp, self.totp_setup = totp, totp_setup
        self.cfg = totp_setup.load_config()
        if not self.cfg and (ROOT / "config.example.json").exists():
            shutil.copy(ROOT / "config.example.json", ROOT / "config.json")
            self.cfg = totp_setup.load_config()
        self.minutes.set(str(self.cfg.get("unlock_minutes", 60)))
        self.status.config(text="Ready. Click Next.", fg="#4ade80")
        self.bar.pack_forget()
        self.next_btn.config(state="normal")

    # ---------- step 2: authenticator ----------
    def page_1(self):
        existing = self.cfg.get("totp_secret", "")
        self.keep_existing = False
        if existing:
            self.label("An authenticator is already set up on this computer, so it will be kept. "
                       "Click Next.", pad=(14, 8))
            self.keep_existing = True
            return
        self.secret = self.totp_setup.ensure_secret(force_new=True)
        self.label("This lock stops strangers from controlling your computer.\n"
                   "1. Open Google or Microsoft Authenticator on your phone.\n"
                   "2. Tap + and scan this picture.", pad=(10, 4))
        try:
            import qrcode
            from PIL import ImageTk
            uri = self.totp.otpauth_uri(self.secret, socket.gethostname())
            img = qrcode.make(uri).convert("RGB").resize((220, 220))
            self.qr_photo = ImageTk.PhotoImage(img)
            tk.Label(self.body, image=self.qr_photo, bg=CARD).pack(pady=4)
        except Exception:
            self.label(f"Could not draw the picture. In your app choose 'enter a setup key':\n{self.secret}",
                       color="#fbbf24")
        self.label("3. Type the 6 digits your app now shows:", pad=(6, 2))
        self.code_var = tk.StringVar()
        self.entry(self.code_var, width=12)
        self.msg = self.label("", color="#f87171", pad=(0, 0))

    def leave_1(self):
        if self.keep_existing:
            return True
        code = self.code_var.get().replace(" ", "")
        if self.totp.verify(self.secret, code) is None:
            self.msg.config(text="That code did not match. Wait for the next code and try again.")
            return False
        self.cfg = self.totp_setup.load_config()
        return True

    # ---------- step 3: ngrok ----------
    def page_2(self):
        self.ngrok_path = find_ngrok()
        if not self.ngrok_path:
            self.label("Installing ngrok...", color=MUTED)
            self.update_idletasks()
            run(["winget", "install", "ngrok.ngrok", "--accept-package-agreements",
                 "--accept-source-agreements", "--silent"])
            self.ngrok_path = find_ngrok()
            self.clear()
        if not self.ngrok_path:
            self.label("ngrok could not be installed automatically. Download it, install it, "
                       "then open this setup again.", color="#f87171")
            self.link("Download ngrok", "https://ngrok.com/download")
            self.next_btn.config(state="disabled")
            return
        self.label("This gives your computer a private address Claude can reach.", pad=(10, 4))
        self.link("1. Open ngrok and sign in (free)", "https://dashboard.ngrok.com/get-started/your-authtoken")
        self.label("Copy your Authtoken, then paste it here:", pad=(8, 2))
        self.token_var = tk.StringVar()
        self.entry(self.token_var)
        self.paste_button(self.token_var)
        self.link("2. Open Domains and create your free domain", "https://dashboard.ngrok.com/domains")
        self.label("Copy the domain (like name.ngrok-free.dev), then paste it here:", pad=(8, 2))
        self.domain_var = tk.StringVar(value=self.cfg.get("ngrok_domain", ""))
        self.entry(self.domain_var)
        self.paste_button(self.domain_var)
        self.msg = self.label("", color="#f87171", pad=(0, 0))

    def leave_2(self):
        domain = self.domain_var.get().replace("https://", "").replace("http://", "").strip("/ ")
        if "." not in domain:
            self.msg.config(text="Please paste your ngrok domain, for example name.ngrok-free.dev")
            return False
        token = self.token_var.get().strip()
        if token and run([self.ngrok_path, "config", "add-authtoken", token]) != 0:
            self.msg.config(text="ngrok did not accept that token. Check it and try again.")
            return False
        self.cfg["ngrok_domain"] = domain
        return True

    # ---------- step 4: options ----------
    def page_3(self):
        self.label("Almost there. Two simple choices:", pad=(10, 6))
        self.label("How long should one unlock last? (shorter is safer)")
        box = ttk.Combobox(self.body, textvariable=self.minutes, values=["10", "20", "30", "60"], width=8,
                           state="readonly", font=("Segoe UI", 11))
        box.pack(anchor="w", padx=18, pady=(0, 2))
        self.label("minutes", size=9, color=MUTED, pad=(0, 10))
        tk.Checkbutton(self.body, text="Start CloudLap automatically when I sign in to Windows",
                       variable=self.autostart, bg=CARD, fg=TEXT, selectcolor=BG, activebackground=CARD,
                       activeforeground=TEXT, wraplength=440, justify="left",
                       font=("Segoe UI", 11)).pack(anchor="w", padx=18, pady=6)
        self.label("Claude can use files in your user folder only. You can narrow this later.",
                   size=9, color=MUTED)

    def leave_3(self):
        try:
            self.cfg["unlock_minutes"] = max(1, int(self.minutes.get()))
        except ValueError:
            self.cfg["unlock_minutes"] = 10
        self.totp_setup.save_config(self.cfg)
        watchdog = ROOT / "watchdog.ps1"
        if self.autostart.get() and watchdog.exists():
            startup = (Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu"
                       / "Programs" / "Startup")
            startup.mkdir(parents=True, exist_ok=True)
            (startup / "CloudLap Watchdog.vbs").write_text(
                "' Starts CloudLap at login. Delete this file to turn auto-start off.\n"
                'CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -WindowStyle Hidden '
                f'-ExecutionPolicy Bypass -File ""{watchdog}""", 0, False\n', encoding="utf-8")
        if watchdog.exists():
            subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
                 "-File", str(watchdog)], cwd=ROOT, creationflags=NO_WINDOW | 0x00000008)
        return True

    # ---------- step 5: finish ----------
    def page_4(self):
        port = int(self.cfg.get("port", 8787))
        up = False
        for _ in range(15):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=1):
                    up = True
                    break
            except OSError:
                time.sleep(1)
        url = f"https://{self.cfg.get('ngrok_domain', '')}/mcp"
        self.label("CloudLap is running." if up else
                   "CloudLap is starting. If it does not come up, open CloudLap.bat to see why.",
                   color="#4ade80" if up else "#fbbf24", pad=(10, 6))
        self.label("Last step, in Claude:\n1. Settings > Connectors > Add custom connector\n"
                   "2. Paste this address (keep it private):")
        e = tk.Entry(self.body, font=("Segoe UI", 11), bg=BG, fg=TEXT, relief="flat", width=46)
        e.insert(0, url)
        e.config(state="readonly")
        e.pack(anchor="w", padx=18, pady=2, ipady=6)

        def copy():
            self.clipboard_clear()
            self.clipboard_append(url)
        tk.Button(self.body, text="Copy address", bg=ACCENT, fg="white", relief="flat", padx=12, pady=5,
                  command=copy).pack(anchor="w", padx=18, pady=6)
        self.label("3. To use it, open your authenticator and tell Claude:\n"
                   '   "Connect to CloudLap, code is 123456" (the real code)')
        self.next_btn.config(text="Done")


if __name__ == "__main__":
    Wizard().mainloop()
