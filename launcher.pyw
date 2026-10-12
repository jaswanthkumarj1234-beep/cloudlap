"""
CloudLap - connect Claude to your laptop from anywhere.

A small desktop app to start, stop and monitor the CloudLap server and its ngrok tunnel.
Uses only the Python standard library plus psutil (already in requirements.txt).
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox

import psutil

# When running as a PyInstaller .exe, __file__ points to a temp dir.
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

SERVER_SCRIPT = APP_DIR / "server.py"
CONFIG_PATH = APP_DIR / "config.json"
AUDIT_PATH = APP_DIR / "audit_log.jsonl"
WATCHDOG = APP_DIR / "watchdog.ps1"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Colours (dark theme)
BG = "#0d1117"
CARD = "#161b22"
BORDER = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
ACCENT = "#2f81f7"
ACCENT_HOVER = "#4c94f8"
GREEN = "#3fb950"
RED = "#f85149"
AMBER = "#d29922"
INPUT = "#0d1117"


# ---------------------------------------------------------------------------
# Small pure helpers (easy to test, no UI)
# ---------------------------------------------------------------------------
def read_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def lock_enabled(cfg: dict) -> bool:
    return bool(cfg.get("totp_secret"))


def clean_domain(value: str) -> str:
    return value.replace("https://", "").replace("http://", "").strip("/ ")


def connector_url(cfg: dict) -> str:
    domain = clean_domain(cfg.get("ngrok_domain", ""))
    return f"https://{domain}/mcp" if domain else ""


def format_audit_line(line: str) -> str:
    """Turn one audit_log.jsonl line into 'HH:MM:SS  tool  status'. Never shows arguments."""
    try:
        rec = json.loads(line)
    except Exception:
        return ""
    ts = str(rec.get("ts", ""))
    clock = ts[11:19] if len(ts) >= 19 and ts[10] in "T " else ts[-8:]
    return f"{clock}  {rec.get('tool', '?')}  {rec.get('status', '')}".rstrip()


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False


def process_running(name: str) -> bool:
    name = name.lower()
    for p in psutil.process_iter(["name"]):
        try:
            if (p.info.get("name") or "").lower() == name:
                return True
        except Exception:
            continue
    return False


def watchdog_pids() -> list:
    pids = []
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            cmd = " ".join(p.info.get("cmdline") or [])
            if "watchdog.ps1" in cmd.lower():
                pids.append(p.pid)
        except Exception:
            continue
    return pids


def startup_file() -> Path:
    return (Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu"
            / "Programs" / "Startup" / "CloudLap Watchdog.vbs")


def find_ngrok() -> str:
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = [APP_DIR / "ngrok.exe", Path(local) / "ngrok" / "ngrok.exe",
                  Path(local) / "Microsoft" / "WinGet" / "Links" / "ngrok.exe"]
    pkgs = Path(local) / "Microsoft" / "WinGet" / "Packages"
    if pkgs.exists():
        candidates += list(pkgs.glob("ngrok*/ngrok.exe"))
    for c in candidates:
        if c.exists():
            return str(c)
    return shutil.which("ngrok") or "ngrok"


def find_python() -> str:
    exe = sys.executable
    if getattr(sys, "frozen", False):
        local = os.environ.get("LOCALAPPDATA", "")
        for ver in ("Python312", "Python313", "Python311", "Python310"):
            p = Path(local) / "Programs" / "Python" / ver / "python.exe"
            if p.exists():
                return str(p)
        return shutil.which("python") or shutil.which("py") or "python"
    if "pythonw" in exe.lower():
        exe = exe.lower().replace("pythonw", "python")
    return exe


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
class FlatButton(tk.Label):
    """A flat button with hover colours (tk.Button looks dated on Windows)."""

    def __init__(self, parent, text, command, bg, hover, fg=TEXT, font=("Segoe UI", 10, "bold"),
                 padx=16, pady=8):
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
            self.config(cursor="hand2" if enabled else "arrow")


class StatusRow(tk.Frame):
    def __init__(self, parent, label):
        super().__init__(parent, bg=CARD)
        self.dot = tk.Canvas(self, width=12, height=12, bg=CARD, highlightthickness=0)
        self.dot.pack(side="left", padx=(0, 10), pady=2)
        self._oval = self.dot.create_oval(1, 1, 11, 11, fill=MUTED, outline="")
        tk.Label(self, text=label, bg=CARD, fg=TEXT, font=("Segoe UI", 11)).pack(side="left")
        self.value = tk.Label(self, text="", bg=CARD, fg=MUTED, font=("Segoe UI", 10))
        self.value.pack(side="right")

    def set(self, text, colour):
        self.dot.itemconfig(self._oval, fill=colour)
        self.value.config(text=text, fg=colour if colour != MUTED else MUTED)


def card(parent, title=None):
    outer = tk.Frame(parent, bg=BORDER)
    inner = tk.Frame(outer, bg=CARD, padx=16, pady=14)
    inner.pack(fill="both", expand=True, padx=1, pady=1)
    if title:
        tk.Label(inner, text=title.upper(), bg=CARD, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 8))
    return outer, inner


class CloudLapApp:
    def __init__(self, root):
        self.root = root
        root.title("CloudLap")
        root.geometry("560x720")
        root.minsize(520, 640)
        root.configure(bg=BG)

        self.server_proc = None
        self.tunnel_proc = None
        self.busy = False
        self.cfg = read_config()
        self._audit_pos = 0
        self._last_state = None

        self.build_ui()
        self.dark_title_bar()
        self.load_recent_activity()
        self.log("Ready.")
        self.refresh_async()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---- window niceties -------------------------------------------------
    def dark_title_bar(self):
        try:
            import ctypes
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:
            pass

    # ---- layout ----------------------------------------------------------
    def build_ui(self):
        pad = 24
        head = tk.Frame(self.root, bg=BG)
        head.pack(fill="x", padx=pad, pady=(22, 2))
        left = tk.Frame(head, bg=BG)
        left.pack(side="left")
        tk.Label(left, text="CloudLap", bg=BG, fg=TEXT, font=("Segoe UI Semibold", 22)).pack(anchor="w")
        tk.Label(left, text="Use Claude on your own computer, from anywhere", bg=BG, fg=MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w")
        self.pill = tk.Label(head, text="OFFLINE", bg=BORDER, fg=MUTED, font=("Segoe UI", 9, "bold"),
                             padx=12, pady=4)
        self.pill.pack(side="right", pady=6)

        # Status
        outer, inner = card(self.root, "Status")
        outer.pack(fill="x", padx=pad, pady=(18, 10))
        self.row_server = StatusRow(inner, "Server")
        self.row_server.pack(fill="x", pady=4)
        self.row_tunnel = StatusRow(inner, "Tunnel (ngrok)")
        self.row_tunnel.pack(fill="x", pady=4)
        self.row_lock = StatusRow(inner, "Authenticator lock")
        self.row_lock.pack(fill="x", pady=4)

        # Setup banner (shown only when something needs attention)
        self.banner = tk.Frame(self.root, bg="#2d2208", highlightthickness=1, highlightbackground="#5a4410")
        self.banner_text = tk.Label(self.banner, text="", bg="#2d2208", fg=AMBER, font=("Segoe UI", 10),
                                    justify="left", wraplength=360)
        self.banner_text.pack(side="left", padx=14, pady=10, fill="x", expand=True)
        self.banner_btn = FlatButton(self.banner, "Fix", self.run_setup, bg="#5a4410", hover="#7a5c16",
                                     fg=TEXT, font=("Segoe UI", 9, "bold"), padx=12, pady=6)
        self.banner_btn.pack(side="right", padx=12, pady=8)

        # Address
        outer, inner = card(self.root, "Connector address")
        outer.pack(fill="x", padx=pad, pady=(0, 10))
        self.addr_card = outer
        row = tk.Frame(inner, bg=CARD)
        row.pack(fill="x")
        self.url_var = tk.StringVar(value="")
        self.url_entry = tk.Entry(row, textvariable=self.url_var, font=("Consolas", 11), bg=INPUT, fg=TEXT,
                                  readonlybackground=INPUT, relief="flat", state="readonly",
                                  highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))
        self.btn_copy = FlatButton(row, "Copy", self.copy_url, bg=ACCENT, hover=ACCENT_HOVER, fg="#ffffff")
        self.btn_copy.pack(side="right")
        tk.Label(inner, text="In Claude: Settings > Connectors > Add custom connector. Keep this address private.",
                 bg=CARD, fg=MUTED, font=("Segoe UI", 9), wraplength=470, justify="left").pack(anchor="w", pady=(8, 0))

        # Main button
        self.btn_main = FlatButton(self.root, "Start CloudLap", self.toggle, bg=GREEN, hover="#56d364",
                                   fg="#04130a", font=("Segoe UI Semibold", 14), pady=14)
        self.btn_main.pack(fill="x", padx=pad, pady=(2, 10))

        # Auto start
        self.auto_var = tk.BooleanVar(value=startup_file().exists())
        self.chk_auto = tk.Checkbutton(
            self.root, text="Start CloudLap when I sign in to Windows", variable=self.auto_var,
            command=self.toggle_autostart, bg=BG, fg=TEXT, selectcolor=CARD, activebackground=BG,
            activeforeground=TEXT, font=("Segoe UI", 10), bd=0, highlightthickness=0, cursor="hand2")
        self.chk_auto.pack(anchor="w", padx=pad - 2, pady=(0, 10))
        if not WATCHDOG.exists():
            self.chk_auto.config(state="disabled")

        # Activity
        outer, inner = card(self.root, "Recent activity")
        outer.pack(fill="both", expand=True, padx=pad, pady=(0, 8))
        self.log_text = tk.Text(inner, font=("Consolas", 9), bg=INPUT, fg=MUTED, relief="flat", height=7,
                                wrap="none", state="disabled", highlightthickness=0, padx=8, pady=6)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_configure("app", foreground=TEXT)
        self.log_text.tag_configure("bad", foreground=RED)
        self.log_text.tag_configure("good", foreground=GREEN)

        # Footer
        foot = tk.Frame(self.root, bg=BG)
        foot.pack(fill="x", padx=pad, pady=(0, 14))
        for text, cmd in (("Setup guide", self.open_guide), ("Open folder", self.open_folder),
                          ("Set up again", self.run_setup)):
            lbl = tk.Label(foot, text=text, bg=BG, fg=ACCENT, font=("Segoe UI", 9, "underline"), cursor="hand2")
            lbl.pack(side="left", padx=(0, 16))
            lbl.bind("<Button-1>", lambda e, c=cmd: c())

    # ---- logging -----------------------------------------------------------
    def _append(self, text, tag=None):
        self.log_text.config(state="normal")
        self.log_text.insert("end", text + "\n", tag or ())
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > 200:
            self.log_text.delete("1.0", f"{lines - 200}.0")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def log(self, msg, tag="app"):
        self._append(f"{time.strftime('%H:%M:%S')}  {msg}", tag)

    def load_recent_activity(self):
        try:
            size = AUDIT_PATH.stat().st_size
            with open(AUDIT_PATH, "rb") as f:
                f.seek(max(0, size - 20000))
                lines = f.read().decode("utf-8", "ignore").splitlines()[-6:]
            for line in lines:
                text = format_audit_line(line)
                if text:
                    self._append(text)
            self._audit_pos = size
        except Exception:
            self._audit_pos = 0

    def poll_audit(self):
        try:
            size = AUDIT_PATH.stat().st_size
            if size < self._audit_pos:
                self._audit_pos = 0
            if size > self._audit_pos:
                with open(AUDIT_PATH, "rb") as f:
                    f.seek(self._audit_pos)
                    data = f.read(size - self._audit_pos).decode("utf-8", "ignore")
                self._audit_pos = size
                for line in data.splitlines():
                    text = format_audit_line(line)
                    if text:
                        self._append(text, "bad" if "LOCKED" in text or "FAILED" in text else None)
        except Exception:
            pass

    # ---- state refresh -----------------------------------------------------
    def refresh_async(self):
        threading.Thread(target=self._refresh_worker, daemon=True).start()
        self.root.after(3000, self.refresh_async)

    def _refresh_worker(self):
        cfg = read_config()
        port = int(cfg.get("port", 8787) or 8787)
        state = {
            "cfg": cfg,
            "server": port_open(port),
            "tunnel": process_running("ngrok.exe"),
        }
        try:
            self.root.after(0, lambda: self.apply_state(state))
        except Exception:
            pass

    def apply_state(self, st):
        self.cfg = st["cfg"]
        server, tunnel = st["server"], st["tunnel"]
        locked_on = lock_enabled(self.cfg)
        url = connector_url(self.cfg)

        self.row_server.set("Running" if server else "Stopped", GREEN if server else MUTED)
        self.row_tunnel.set("Connected" if tunnel else "Stopped", GREEN if tunnel else MUTED)
        self.row_lock.set("On" if locked_on else "Not set up", GREEN if locked_on else AMBER)
        self.url_var.set(url if url else "Set your ngrok domain first (use Set up again)")

        online = server and tunnel
        self.pill.config(text="ONLINE" if online else "OFFLINE", bg="#12301a" if online else BORDER,
                         fg=GREEN if online else MUTED)

        if not self.busy:
            if server or tunnel:
                self.btn_main.set(text="Stop CloudLap", bg=RED, hover="#ff6a63", enabled=True)
                self.btn_main.config(fg="#ffffff")
            else:
                self.btn_main.set(text="Start CloudLap", bg=GREEN, hover="#56d364", enabled=True)
                self.btn_main.config(fg="#04130a")

        problem = None
        if not url:
            problem = "No ngrok domain is set, so Claude cannot reach this computer."
        elif not locked_on:
            problem = ("The authenticator lock is not set up. Anyone with your address could control this "
                       "computer. Set it up now.")
        if problem:
            self.banner_text.config(text=problem)
            self.banner.pack(fill="x", padx=24, pady=(0, 10), before=self.addr_card)
        else:
            self.banner.pack_forget()

        self.poll_audit()

    # ---- actions -----------------------------------------------------------
    def toggle(self):
        if self.busy:
            return
        if port_open(int(self.cfg.get("port", 8787) or 8787)) or process_running("ngrok.exe"):
            self.stop()
        else:
            self.start()

    def start(self):
        if not connector_url(self.cfg):
            messagebox.showinfo("CloudLap", "Set your ngrok domain first. Click 'Set up again' at the bottom.")
            return
        self.busy = True
        self.btn_main.set(text="Starting...", bg=BORDER, enabled=False)
        threading.Thread(target=self._start_worker, daemon=True).start()

    def _ui(self, fn):
        self.root.after(0, fn)

    def _start_worker(self):
        try:
            cfg = read_config()
            port = int(cfg.get("port", 8787) or 8787)
            if not port_open(port):
                self._ui(lambda: self.log("Starting server..."))
                logf = open(APP_DIR / "server.log", "a", encoding="utf-8")
                self.server_proc = subprocess.Popen([find_python(), str(SERVER_SCRIPT)], cwd=str(APP_DIR),
                                                    stdout=logf, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
                for _ in range(40):
                    if port_open(port):
                        break
                    if self.server_proc.poll() is not None:
                        self._ui(lambda: self.log("Server stopped right after starting. See server.log.", "bad"))
                        return
                    time.sleep(0.5)
                else:
                    self._ui(lambda: self.log("Server did not start in time. See server.log.", "bad"))
                    return
                self._ui(lambda: self.log("Server running.", "good"))
            if not process_running("ngrok.exe"):
                self._ui(lambda: self.log("Connecting tunnel..."))
                domain = clean_domain(cfg.get("ngrok_domain", ""))
                self.tunnel_proc = subprocess.Popen(
                    [find_ngrok(), "http", f"--url={domain}", f"127.0.0.1:{port}"], cwd=str(APP_DIR),
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)
                time.sleep(4)
                if self.tunnel_proc.poll() is not None:
                    self._ui(lambda: self.log("The tunnel could not start. Check your ngrok authtoken and domain.",
                                              "bad"))
                    return
                self._ui(lambda: self.log("Tunnel connected.", "good"))
            if lock_enabled(cfg):
                self._ui(lambda: self.log("Online. Unlock with your authenticator code when you chat.", "good"))
            else:
                self._ui(lambda: self.log("Online, but NOT protected. Set up the authenticator lock.", "bad"))
        except Exception as exc:
            self._ui(lambda: self.log(f"Error: {exc}", "bad"))
        finally:
            self.busy = False
            self._ui(self.refresh_async_once)

    def refresh_async_once(self):
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def stop(self):
        guards = watchdog_pids()
        if guards:
            if not messagebox.askyesno(
                    "CloudLap",
                    "CloudLap's auto-restart helper is running and would bring it straight back.\n\n"
                    "Stop CloudLap and the helper until you next sign in?"):
                return
        self.busy = True
        self.btn_main.set(text="Stopping...", bg=BORDER, enabled=False)
        threading.Thread(target=self._stop_worker, args=(guards,), daemon=True).start()

    def _stop_worker(self, guards):
        try:
            for pid in guards:
                try:
                    psutil.Process(pid).kill()
                except Exception:
                    pass
            port = int(read_config().get("port", 8787) or 8787)
            for proc in psutil.process_iter(["name", "pid"]):
                try:
                    if (proc.info.get("name") or "").lower() == "ngrok.exe":
                        proc.kill()
                except Exception:
                    pass
            try:
                for conn in psutil.net_connections(kind="tcp"):
                    if conn.status == psutil.CONN_LISTEN and conn.laddr and conn.laddr.port == port and conn.pid:
                        psutil.Process(conn.pid).kill()
            except Exception:
                pass
            self.server_proc = None
            self.tunnel_proc = None
            self._ui(lambda: self.log("Stopped."))
        finally:
            self.busy = False
            self._ui(self.refresh_async_once)

    def copy_url(self):
        url = connector_url(self.cfg)
        if not url:
            messagebox.showinfo("CloudLap", "Set your ngrok domain first.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        self.btn_copy.set(text="Copied")
        self.log("Address copied.")
        self.root.after(1800, lambda: self.btn_copy.set(text="Copy"))

    def toggle_autostart(self):
        vbs = startup_file()
        try:
            if self.auto_var.get():
                vbs.parent.mkdir(parents=True, exist_ok=True)
                vbs.write_text(
                    "' Starts CloudLap at login. Delete this file to turn auto-start off.\n"
                    'CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -WindowStyle Hidden '
                    f'-ExecutionPolicy Bypass -File ""{WATCHDOG}""", 0, False\n', encoding="utf-8")
                self.log("Auto-start turned on.")
            else:
                vbs.unlink(missing_ok=True)
                self.log("Auto-start turned off.")
        except Exception as exc:
            self.auto_var.set(vbs.exists())
            self.log(f"Could not change auto-start: {exc}", "bad")

    def run_setup(self):
        wizard = APP_DIR / "setup_gui.pyw"
        if not wizard.exists():
            messagebox.showinfo("CloudLap", "setup_gui.pyw was not found in the CloudLap folder.")
            return
        py = Path(find_python())
        pyw = py.with_name("pythonw.exe")
        subprocess.Popen([str(pyw if pyw.exists() else py), str(wizard)], cwd=str(APP_DIR))
        self.log("Setup opened in a new window. Restart CloudLap when it finishes.")

    def open_guide(self):
        guide = APP_DIR / "SETUP.md"
        if guide.exists():
            os.startfile(str(guide)) if hasattr(os, "startfile") else webbrowser.open(guide.as_uri())
        else:
            webbrowser.open("https://github.com/jaswanthkumarj1234-beep/cloudlap#readme")

    def open_folder(self):
        if hasattr(os, "startfile"):
            os.startfile(str(APP_DIR))

    def on_close(self):
        if self.server_proc is not None or self.tunnel_proc is not None:
            choice = messagebox.askyesnocancel(
                "CloudLap", "CloudLap is running because you started it here.\n\n"
                            "Yes: stop it and close\nNo: leave it running and close\nCancel: go back")
            if choice is None:
                return
            if choice:
                for proc in (self.tunnel_proc, self.server_proc):
                    try:
                        if proc:
                            proc.terminate()
                    except Exception:
                        pass
        self.root.destroy()


def main():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    CloudLapApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
