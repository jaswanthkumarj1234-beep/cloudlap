"""CloudLap setup - a plain window, no terminal, no typing commands.

Opened by "Start CloudLap.bat" the first time. Five short steps: install, authenticator,
ngrok, options, finish. Safe to run again. Uses only the Python standard library until the
install step finishes. Matches the look of launcher.pyw.
"""

import io
import os
import shutil
import socket
import subprocess
import sys
import re
import threading
import time
import urllib.request
import webbrowser
import zipfile
import tkinter as tk
from tkinter import ttk
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Same palette as the CloudLap window
BG, CARD, BORDER = "#0d1117", "#161b22", "#30363d"
TEXT, MUTED = "#e6edf3", "#8b949e"
ACCENT, ACCENT_HOVER = "#2f81f7", "#4c94f8"
GREEN, RED, AMBER = "#3fb950", "#f85149", "#d29922"
INPUT = "#0d1117"
NO_WINDOW = 0x08000000 if os.name == "nt" else 0
NGROK_ZIP = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
LOCAL = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))


def find_ngrok() -> str:
    own = LOCAL / "ngrok" / "ngrok.exe"
    if own.exists():
        return str(own)
    found = shutil.which("ngrok")
    if found:
        return found
    cands = [LOCAL / "Microsoft" / "WinGet" / "Links" / "ngrok.exe"]
    pkgs = LOCAL / "Microsoft" / "WinGet" / "Packages"
    if pkgs.exists():
        cands += list(pkgs.glob("ngrok*/ngrok.exe"))
    for c in cands:
        if c.exists():
            return str(c)
    return ""


def has_authtoken() -> bool:
    for base in (LOCAL / "ngrok", Path(os.environ.get("APPDATA", "")) / "ngrok"):
        f = base / "ngrok.yml"
        try:
            if f.exists() and "authtoken" in f.read_text(encoding="utf-8", errors="ignore"):
                return True
        except OSError:
            pass
    return False


def run(cmd: list, timeout: int = 60) -> int:
    try:
        return subprocess.call(cmd, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, creationflags=NO_WINDOW, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return 1


def download_ngrok(progress) -> str:
    dest = LOCAL / "ngrok"
    dest.mkdir(parents=True, exist_ok=True)
    progress("Downloading ngrok (about 10 MB)...")
    with urllib.request.urlopen(NGROK_ZIP, timeout=60) as resp:
        data = resp.read()
    progress("Unpacking ngrok...")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extract("ngrok.exe", dest)
    return str(dest / "ngrok.exe")


def _ngrok_error(text: str, domain: str) -> str:
    m = re.search(r"ERR_NGROK_(\d+)", text)
    code = m.group(0) if m else ""
    n = m.group(1) if m else ""
    if n == "108":
        return ("Your ngrok account is already connected on another computer (a free account allows "
                "one at a time). Stop CloudLap there first, then test again.")
    if n in ("105", "106", "107", "121"):
        return "ngrok did not accept your Authtoken. Copy it again from the Authtoken page and paste it."
    if n == "334":
        return (f"{domain} is already online somewhere else (another computer, or CloudLap is already "
                "running here). Stop it there first, or use a different domain.")
    if code:
        return (f"ngrok refused the domain ({code}). Use the domain shown on your ngrok Domains page, "
                "created in the same account as the Authtoken.")
    return "Could not reach ngrok. Check your internet connection and try again."


def test_tunnel(ngrok: str, token: str, domain: str, port: int):
    """Open the tunnel for a few seconds. Returns (ok, message)."""
    if token and run([ngrok, "config", "add-authtoken", token], timeout=30) != 0:
        return False, "ngrok did not accept that Authtoken. Copy it again and paste it."
    # CloudLap itself may already be online on this domain
    try:
        with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2) as r:
            if domain in r.read().decode("utf-8", "ignore"):
                return True, f"Connected. {domain} is already online from this computer."
    except Exception:
        pass
    proc = subprocess.Popen(
        [ngrok, "http", f"--url={domain}", f"127.0.0.1:{port}", "--log=stdout", "--log-format=json"],
        cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        creationflags=NO_WINDOW, text=True, encoding="utf-8", errors="ignore")
    lines = []

    def reader():
        for line in proc.stdout:
            lines.append(line)
    threading.Thread(target=reader, daemon=True).start()
    ok, start = False, time.time()
    try:
        while time.time() - start < 25:
            text = "".join(lines)
            if "started tunnel" in text and domain in text:
                ok = True
                break
            if proc.poll() is not None or "ERR_NGROK_" in text:
                time.sleep(0.5)
                break
            time.sleep(0.5)
    finally:
        try:
            proc.kill()
        except OSError:
            pass
    if ok:
        return True, f"Connected. ngrok accepted your Authtoken and {domain}."
    return False, _ngrok_error("".join(lines), domain)


class FlatButton(tk.Label):
    def __init__(self, parent, text, command, bg=ACCENT, hover=ACCENT_HOVER, fg=TEXT,
                 font=("Segoe UI", 10, "bold"), padx=16, pady=8):
        super().__init__(parent, text=text, bg=bg, fg=fg, font=font, padx=padx, pady=pady, cursor="hand2")
        self._bg, self._hover, self._cmd, self._enabled = bg, hover, command, True
        self.bind("<Enter>", lambda e: self._enabled and self.config(bg=self._hover))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg))
        self.bind("<Button-1>", lambda e: self._enabled and self._cmd())

    def set(self, text=None, bg=None, hover=None, enabled=None):
        if text is not None:
            self.config(text=text)
        if bg is not None:
            self._bg = bg
            self.config(bg=bg)
        if hover is not None:
            self._hover = hover
        if enabled is not None:
            self._enabled = enabled
            self.config(cursor="hand2" if enabled else "arrow", fg=TEXT if enabled else MUTED)
            if not enabled:
                self.config(bg=BORDER)
                self._bg = BORDER
            else:
                self._bg = ACCENT
                self._hover = ACCENT_HOVER
                self.config(bg=ACCENT)


class Wizard(tk.Tk):
    STEPS = ["Install", "Authenticator", "ngrok", "Options", "Finish"]
    SUBTITLES = [
        "Getting CloudLap ready",
        "Protect your computer with a code from your phone",
        "Give your computer a private address for Claude",
        "Choose how long each unlock lasts",
        "Connect CloudLap to Claude",
    ]

    def __init__(self):
        super().__init__()
        self.title("CloudLap setup")
        self.configure(bg=BG)
        self.geometry("560x760")
        self.minsize(520, 700)
        self.cfg = {}
        self.totp = None
        self.totp_setup = None
        self.secret = ""
        self.qr_photo = None
        self.ngrok_path = ""
        self.keep_existing = False
        self.autostart = tk.BooleanVar(value=True)
        self.minutes = tk.StringVar(value="60")
        self.step = 0
        self.busy = False
        self.form_ready = False
        self.tested_key = None
        self.skip_key = None

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Horizontal.TProgressbar", troughcolor=BORDER, background=ACCENT,
                        bordercolor=BORDER, lightcolor=ACCENT, darkcolor=ACCENT)

        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=24, pady=(22, 0))
        tk.Label(head, text="CloudLap", bg=BG, fg=TEXT, font=("Segoe UI Semibold", 22)).pack(anchor="w")
        tk.Label(head, text="Setup", bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w")

        self.dots = tk.Frame(self, bg=BG)
        self.dots.pack(fill="x", padx=24, pady=(14, 4))
        self.dot_labels = []
        for i, name in enumerate(self.STEPS):
            lbl = tk.Label(self.dots, text=f"{i + 1}  {name}", bg=BG, fg=MUTED, font=("Segoe UI", 9))
            lbl.pack(side="left", padx=(0, 14))
            self.dot_labels.append(lbl)

        self.sub = tk.Label(self, text="", bg=BG, fg=TEXT, font=("Segoe UI Semibold", 14), anchor="w")
        self.sub.pack(fill="x", padx=24, pady=(10, 8))

        outer = tk.Frame(self, bg=BORDER)
        outer.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        self.body = tk.Frame(outer, bg=CARD, padx=18, pady=16)
        self.body.pack(fill="both", expand=True, padx=1, pady=1)

        foot = tk.Frame(self, bg=BG)
        foot.pack(fill="x", padx=24, pady=(0, 20))
        self.back_btn = FlatButton(foot, "Back", self.go_back, bg=CARD, hover=BORDER, fg=MUTED)
        self.next_btn = FlatButton(foot, "Next", self.go_next, padx=28)
        self.next_btn.pack(side="right")

        self.update_idletasks()
        self.dark_title_bar()
        self.show_step()

    def dark_title_bar(self):
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:
            pass

    # ---------- building blocks ----------
    def clear(self):
        for w in self.body.winfo_children():
            w.destroy()

    def text(self, content, size=10, color=TEXT, bold=False, pad=(0, 8)):
        lbl = tk.Label(self.body, text=content, bg=CARD, fg=color, justify="left", wraplength=470,
                       font=("Segoe UI Semibold" if bold else "Segoe UI", size))
        lbl.pack(anchor="w", pady=pad)
        return lbl

    def button(self, label, command, bg=BORDER, hover="#3d444d", pad=(0, 6)):
        b = FlatButton(self.body, label, command, bg=bg, hover=hover, padx=14, pady=6,
                       font=("Segoe UI", 10))
        b.pack(anchor="w", pady=pad)
        return b

    def field(self, var, width=44):
        e = tk.Entry(self.body, textvariable=var, width=width, font=("Segoe UI", 11), bg=INPUT, fg=TEXT,
                     insertbackground=TEXT, relief="flat", highlightthickness=1,
                     highlightbackground=BORDER, highlightcolor=ACCENT)
        e.pack(anchor="w", pady=(0, 4), ipady=7)
        return e

    def paste_button(self, var):
        def paste():
            try:
                var.set(self.clipboard_get().strip())
            except tk.TclError:
                pass
        b = FlatButton(self.body, "Paste from clipboard", paste, bg=CARD, hover=BORDER, fg=MUTED,
                       padx=0, pady=2, font=("Segoe UI", 9))
        b.pack(anchor="w", pady=(0, 8))

    def opener(self, url):
        return lambda: webbrowser.open(url)

    def set_next(self, text="Next", enabled=True):
        self.next_btn.set(text=text, enabled=enabled)

    def show_step(self):
        self.clear()
        for i, lbl in enumerate(self.dot_labels):
            if i < self.step:
                lbl.config(fg=GREEN)
            elif i == self.step:
                lbl.config(fg=TEXT, font=("Segoe UI Semibold", 9))
            else:
                lbl.config(fg=MUTED, font=("Segoe UI", 9))
        self.sub.config(text=self.SUBTITLES[self.step])
        self.set_next("Next", True)
        if 2 <= self.step <= 3:
            self.back_btn.pack(side="left")
        else:
            self.back_btn.pack_forget()
        getattr(self, f"page_{self.step}")()

    def go_next(self):
        if self.busy:
            return
        if not getattr(self, f"leave_{self.step}", lambda: True)():
            return
        if self.step == len(self.STEPS) - 1:
            self.launch_app()
            self.destroy()
            return
        self.step += 1
        self.show_step()

    def go_back(self):
        if self.busy or self.step == 0:
            return
        self.step -= 1
        self.show_step()

    def launch_app(self):
        py = Path(sys.executable)
        pyw = py.with_name("pythonw.exe")
        try:
            subprocess.Popen([str(pyw if pyw.exists() else py), str(ROOT / "launcher.pyw")], cwd=ROOT)
        except OSError:
            pass

    # ---------- step 1: install ----------
    def page_0(self):
        if sys.version_info < (3, 10):
            self.text("Python 3.10 or newer is needed. Install it from python.org (tick 'Add Python to "
                      "PATH'), then open CloudLap again.", color=RED)
            self.set_next("Next", False)
            return
        self.text("CloudLap lets Claude reach your computer safely. Setup takes about 5 minutes.",
                  pad=(0, 10))
        self.text("Have ready:\n   -  your phone, with Google or Microsoft Authenticator\n"
                  "   -  a free ngrok account (ngrok.com)", color=MUTED, pad=(0, 14))
        self.status = self.text("Getting things ready...", color=MUTED)
        self.bar = ttk.Progressbar(self.body, mode="indeterminate", length=440)
        self.bar.pack(anchor="w", pady=6)
        self.bar.start(12)
        self.busy = True
        self.set_next("Next", False)
        threading.Thread(target=self.install, daemon=True).start()

    def install(self):
        code = run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "qrcode", "pillow"],
                   timeout=600)
        self.after(0, self.install_done, code)

    def install_done(self, code):
        self.busy = False
        if self.step != 0:
            return
        self.bar.stop()
        if code != 0:
            self.status.config(text="Could not install the needed parts. Check your internet connection, "
                                    "then close this window and open CloudLap again.", fg=RED)
            return
        import totp
        import totp_setup
        self.totp, self.totp_setup = totp, totp_setup
        self.cfg = totp_setup.load_config()
        if not self.cfg and (ROOT / "config.example.json").exists():
            shutil.copy(ROOT / "config.example.json", ROOT / "config.json")
            self.cfg = totp_setup.load_config()
        self.minutes.set(str(self.cfg.get("unlock_minutes", 60)))
        self.status.config(text="Ready. Click Next.", fg=GREEN)
        self.bar.pack_forget()
        self.set_next("Next", True)

    # ---------- step 2: authenticator ----------
    def page_1(self):
        self.keep_existing = bool(self.cfg.get("totp_secret"))
        if self.keep_existing:
            self.text("An authenticator is already set up on this computer, so it will be kept.\n"
                      "Click Next.", pad=(0, 8))
            return
        self.secret = self.totp_setup.ensure_secret(force_new=True)
        self.text("1.  On your phone open Google Authenticator or Microsoft Authenticator.\n"
                  "2.  Tap  +  and scan this picture.", pad=(0, 6))
        try:
            import qrcode
            from PIL import ImageTk
            uri = self.totp.otpauth_uri(self.secret, socket.gethostname())
            img = qrcode.make(uri).convert("RGB").resize((210, 210))
            self.qr_photo = ImageTk.PhotoImage(img)
            tk.Label(self.body, image=self.qr_photo, bg=CARD).pack(anchor="w", pady=6)
        except Exception:
            self.text(f"The picture could not be drawn. In your app choose 'enter a setup key':\n{self.secret}",
                      color=AMBER)
        self.text("3.  Type the 6 digits your app shows now:", pad=(4, 4))
        self.code_var = tk.StringVar()
        self.field(self.code_var, width=14)
        self.msg = self.text("", color=RED, pad=(0, 0))

    def leave_1(self):
        if self.keep_existing:
            return True
        code = self.code_var.get().replace(" ", "")
        if self.totp.verify(self.secret, code) is None:
            self.msg.config(text="That code did not match. Wait for the next code and try again.")
            return False
        self.cfg = self.totp_setup.load_config()
        self.keep_existing = True
        return True

    # ---------- step 3: ngrok ----------
    def page_2(self):
        self.form_ready = False
        self.ngrok_path = find_ngrok()
        if self.ngrok_path:
            self.build_ngrok_form()
            return
        self.text("Setting up ngrok for you. This takes about a minute and needs no clicks.", pad=(0, 10))
        self.status = self.text("Starting...", color=MUTED)
        self.bar = ttk.Progressbar(self.body, mode="indeterminate", length=440)
        self.bar.pack(anchor="w", pady=6)
        self.bar.start(12)
        self.busy = True
        self.set_next("Next", False)
        threading.Thread(target=self.fetch_ngrok, daemon=True).start()

    def say(self, message):
        self.after(0, lambda: self.step == 2 and self.busy and self.status.config(text=message))

    def fetch_ngrok(self):
        path = ""
        try:
            path = download_ngrok(self.say)
        except Exception:
            self.say("Trying another way...")
            run(["winget", "install", "ngrok.ngrok", "--accept-package-agreements",
                 "--accept-source-agreements", "--silent"], timeout=240)
            path = find_ngrok()
        self.after(0, self.ngrok_ready, path)

    def ngrok_ready(self, path):
        self.busy = False
        if self.step != 2:
            return
        self.clear()
        self.ngrok_path = path or find_ngrok()
        if self.ngrok_path:
            self.build_ngrok_form()
        else:
            self.build_ngrok_manual()

    def build_ngrok_manual(self):
        self.form_ready = False
        self.set_next("Check again", True)
        self.text("ngrok could not be set up automatically. Three quick steps:", bold=True, pad=(0, 8))
        self.text("1.  Click the button and download ngrok for Windows (a ZIP file).", pad=(0, 4))
        self.button("Open ngrok download page", self.opener("https://ngrok.com/download"))
        self.text("2.  Open the ZIP and drag  ngrok.exe  into the folder this button opens.", pad=(8, 4))

        def open_folder():
            d = LOCAL / "ngrok"
            d.mkdir(parents=True, exist_ok=True)
            os.startfile(str(d))
        self.button("Open the folder", open_folder)
        self.text("3.  Click  Check again  below.", pad=(8, 4))

    def field_row(self, var):
        row = tk.Frame(self.body, bg=CARD)
        row.pack(anchor="w", pady=(0, 10))
        e = tk.Entry(row, textvariable=var, width=36, font=("Segoe UI", 11), bg=INPUT, fg=TEXT,
                     insertbackground=TEXT, relief="flat", highlightthickness=1,
                     highlightbackground=BORDER, highlightcolor=ACCENT)
        e.pack(side="left", ipady=7)

        def paste():
            try:
                var.set(self.clipboard_get().strip())
            except tk.TclError:
                pass
        FlatButton(row, "Paste", paste, bg=BORDER, hover="#3d444d", padx=12, pady=6,
                   font=("Segoe UI", 9)).pack(side="left", padx=(8, 0))
        var.trace_add("write", lambda *a: self.on_edit())

    def head_row(self, label, button_text, url):
        row = tk.Frame(self.body, bg=CARD)
        row.pack(fill="x", pady=(0, 4))
        tk.Label(row, text=label, bg=CARD, fg=TEXT, font=("Segoe UI Semibold", 10)).pack(side="left")
        FlatButton(row, button_text, self.opener(url), bg=BORDER, hover="#3d444d", padx=10, pady=4,
                   font=("Segoe UI", 9)).pack(side="right")

    def on_edit(self):
        if self.step == 2 and self.form_ready and self.next_btn.cget("text") != "Next":
            self.set_next("Next", True)

    def build_ngrok_form(self):
        self.form_ready = True
        self.text("ngrok gives your laptop a private web address, so Claude on your phone or any other "
                  "device can reach it. It is free. Sign up at ngrok.com, then copy two things:",
                  size=9, color=MUTED, pad=(0, 8))
        FlatButton(self.body, "Open ngrok sign-up", self.opener("https://dashboard.ngrok.com/signup"),
                   bg=BORDER, hover="#3d444d", padx=12, pady=5, font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 12))
        self.head_row("1.  Your Authtoken", "Open Authtoken page",
                      "https://dashboard.ngrok.com/get-started/your-authtoken")
        self.token_var = tk.StringVar()
        self.field_row(self.token_var)
        self.head_row("2.  Your free domain (name.ngrok-free.dev)", "Open Domains page",
                      "https://dashboard.ngrok.com/domains")
        self.domain_var = tk.StringVar(value=self.cfg.get("ngrok_domain", ""))
        self.field_row(self.domain_var)
        self.text("No domain listed? Click  Create domain  on that page and copy what it shows.",
                  size=9, color=MUTED, pad=(0, 8))
        self.test_btn = FlatButton(self.body, "Test connection", lambda: self.run_test(advance=False),
                                   padx=14, pady=7)
        self.test_btn.pack(anchor="w", pady=(0, 6))
        self.msg = self.text("", color=RED, pad=(0, 0))

    def read_fields(self):
        domain = self.domain_var.get().replace("https://", "").replace("http://", "").strip("/ ")
        return self.token_var.get().strip(), domain

    def validate_fields(self):
        token, domain = self.read_fields()
        if "." not in domain:
            self.msg.config(text="Paste your ngrok domain, for example name.ngrok-free.dev", fg=RED)
            return None
        if not token and not has_authtoken():
            self.msg.config(text="Paste your ngrok Authtoken first (step 1).", fg=RED)
            return None
        return token, domain

    def run_test(self, advance):
        if self.busy:
            return
        fields = self.validate_fields()
        if not fields:
            return
        token, domain = fields
        self.busy = True
        self.msg.config(text="Checking the connection... (up to 25 seconds)", fg=AMBER)
        self.set_next("Next", False)
        port = int(self.cfg.get("port", 8787))

        def work():
            ok, message = test_tunnel(self.ngrok_path, token, domain, port)
            self.after(0, self.test_done, (token, domain), ok, message, advance)
        threading.Thread(target=work, daemon=True).start()

    def test_done(self, key, ok, message, advance):
        self.busy = False
        if self.step != 2:
            return
        self.set_next("Next", True)
        if ok:
            self.tested_key = key
            self.msg.config(text=message, fg=GREEN)
            if advance:
                self.go_next()
            return
        self.msg.config(text=message, fg=RED)
        if advance:
            self.skip_key = key
            self.set_next("Continue anyway", True)

    def leave_2(self):
        if self.busy:
            return False
        if not self.form_ready:
            self.ngrok_path = find_ngrok()
            if self.ngrok_path:
                self.clear()
                self.set_next("Next", True)
                self.build_ngrok_form()
            return False
        fields = self.validate_fields()
        if not fields:
            return False
        token, domain = fields
        if self.tested_key != (token, domain):
            if self.skip_key == (token, domain):
                if token:
                    run([self.ngrok_path, "config", "add-authtoken", token], timeout=30)
            else:
                self.run_test(advance=True)
                return False
        self.cfg["ngrok_domain"] = domain
        return True

    # ---------- step 4: options ----------
    def page_3(self):
        self.text("How long should one unlock last?\nShorter is safer. CloudLap locks itself afterwards.",
                  pad=(0, 8))
        row = tk.Frame(self.body, bg=CARD)
        row.pack(anchor="w", pady=(0, 18))
        self.choice_btns = {}
        for m in ("10", "20", "30", "60"):
            b = FlatButton(row, f"{m} min", lambda v=m: self.pick_minutes(v), bg=BORDER, hover="#3d444d",
                           padx=16, pady=8)
            b.pack(side="left", padx=(0, 8))
            self.choice_btns[m] = b
        self.pick_minutes(self.minutes.get() if self.minutes.get() in self.choice_btns else "60")
        tk.Checkbutton(self.body, text="Start CloudLap automatically when I sign in to Windows",
                       variable=self.autostart, bg=CARD, fg=TEXT, selectcolor=BG, activebackground=CARD,
                       activeforeground=TEXT, wraplength=440, justify="left", font=("Segoe UI", 10),
                       highlightthickness=0, bd=0).pack(anchor="w", pady=6)
        self.text("Claude can only use files in your user folder. You can narrow this later.",
                  size=9, color=MUTED, pad=(0, 0))

    def pick_minutes(self, value):
        self.minutes.set(value)
        for m, b in self.choice_btns.items():
            b._bg = ACCENT if m == value else BORDER
            b._hover = ACCENT_HOVER if m == value else "#3d444d"
            b.config(bg=b._bg)

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
        self.url = f"https://{self.cfg.get('ngrok_domain', '')}/mcp"
        self.up_label = self.text("Starting CloudLap...", color=AMBER, pad=(0, 10))
        self.set_next("Done", True)
        self.tries = 0
        self.after(500, self.poll_server)
        self.text("In Claude:", bold=True, pad=(0, 4))
        self.text("1.  Open  Settings > Connectors > Add custom connector.\n"
                  "2.  Paste this address (keep it private):", pad=(0, 6))
        e = tk.Entry(self.body, font=("Segoe UI", 11), bg=INPUT, fg=TEXT, relief="flat", width=44,
                     highlightthickness=1, highlightbackground=BORDER, readonlybackground=INPUT)
        e.insert(0, self.url)
        e.config(state="readonly")
        e.pack(anchor="w", pady=(0, 6), ipady=7)
        self.copy_btn = FlatButton(self.body, "Copy address", self.copy_url, padx=14, pady=6)
        self.copy_btn.pack(anchor="w", pady=(0, 12))
        self.text("3.  To use it, open your authenticator app and tell Claude:\n"
                  '     "Connect to CloudLap, code is 123456"   (type the real code)', pad=(0, 0))

    def copy_url(self):
        self.clipboard_clear()
        self.clipboard_append(self.url)
        self.copy_btn.set(text="Copied")
        self.after(1800, lambda: self.step == 4 and self.copy_btn.set(text="Copy address"))

    def poll_server(self):
        if self.step != 4:
            return
        port = int(self.cfg.get("port", 8787))
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                self.up_label.config(text="CloudLap is running.", fg=GREEN)
                return
        except OSError:
            pass
        self.tries += 1
        if self.tries >= 20:
            self.up_label.config(text="CloudLap is still starting. Click Done, then press Start in the "
                                      "CloudLap window.", fg=AMBER)
            return
        self.after(1000, self.poll_server)


if __name__ == "__main__":
    Wizard().mainloop()
