"""
CloudLap - Connect Claude to your laptop from anywhere
A visual GUI app to manage your MCP server and Cloudflare tunnel.
"""
import json
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import re
import os
import time

# When running as a PyInstaller .exe, __file__ points to a temp dir.
# Use the exe's actual location instead.
if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

CLOUDFLARED = APP_DIR / "cloudflared.exe"
SERVER_SCRIPT = APP_DIR / "server.py"


class CloudLapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CloudLap")
        self.root.geometry("540x600")
        self.root.resizable(False, False)
        self.root.configure(bg="#0f0f1a")

        # Try to set app icon (won't crash if fails)
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self.server_proc = None
        self.tunnel_proc = None
        self.tunnel_url = None
        self.is_running = False

        self.build_ui()
        self.check_ready()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        bg = "#0f0f1a"
        card_bg = "#1a1a2e"
        accent_blue = "#4361ee"
        green = "#06d6a0"
        red = "#ef476f"
        yellow = "#ffd166"
        white = "#f8f9fa"
        gray = "#6c757d"
        dark_input = "#0b0b15"

        # ─── Header ───
        header = tk.Frame(self.root, bg=bg)
        header.pack(fill="x", padx=24, pady=(20, 4))

        tk.Label(header, text="☁️  CloudLap", font=("Segoe UI", 22, "bold"),
                 bg=bg, fg=white).pack(anchor="w")
        tk.Label(header, text="Your laptop is your cloud. Connect Claude from anywhere.",
                 font=("Segoe UI", 10), bg=bg, fg=gray).pack(anchor="w", pady=(2, 0))

        # ─── Divider ───
        tk.Frame(self.root, bg="#2a2a4a", height=1).pack(fill="x", padx=24, pady=12)

        # ─── Status Panel ───
        status_card = tk.Frame(self.root, bg=card_bg, padx=16, pady=14)
        status_card.pack(fill="x", padx=24, pady=(0, 8))

        # Server row
        r1 = tk.Frame(status_card, bg=card_bg)
        r1.pack(fill="x", pady=3)
        tk.Label(r1, text="MCP Server", font=("Segoe UI", 11), bg=card_bg, fg=white).pack(side="left")
        self.lbl_server = tk.Label(r1, text="⬤  Offline", font=("Segoe UI", 11, "bold"),
                                    bg=card_bg, fg=red)
        self.lbl_server.pack(side="right")

        # Tunnel row
        r2 = tk.Frame(status_card, bg=card_bg)
        r2.pack(fill="x", pady=3)
        tk.Label(r2, text="Cloudflare Tunnel", font=("Segoe UI", 11), bg=card_bg, fg=white).pack(side="left")
        self.lbl_tunnel = tk.Label(r2, text="⬤  Offline", font=("Segoe UI", 11, "bold"),
                                    bg=card_bg, fg=red)
        self.lbl_tunnel.pack(side="right")

        # ─── URL Panel ───
        url_card = tk.Frame(self.root, bg=card_bg, padx=16, pady=14)
        url_card.pack(fill="x", padx=24, pady=(0, 8))

        tk.Label(url_card, text="CONNECTOR URL", font=("Segoe UI", 9, "bold"),
                 bg=card_bg, fg=gray).pack(anchor="w", pady=(0, 6))
        tk.Label(url_card, text="Copy this and paste in Claude → Settings → Connectors → Add",
                 font=("Segoe UI", 8), bg=card_bg, fg="#555").pack(anchor="w", pady=(0, 6))

        url_row = tk.Frame(url_card, bg=card_bg)
        url_row.pack(fill="x")

        self.url_var = tk.StringVar(value="Click START to get your URL...")
        self.url_entry = tk.Entry(url_row, textvariable=self.url_var, font=("Consolas", 11),
                                   bg=dark_input, fg=green, insertbackground=green,
                                   relief="flat", state="readonly", readonlybackground=dark_input,
                                   highlightthickness=1, highlightbackground="#333", highlightcolor=accent_blue)
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))

        self.btn_copy = tk.Button(url_row, text="📋 Copy", font=("Segoe UI", 10, "bold"),
                                   bg=accent_blue, fg=white, relief="flat", padx=14, pady=6,
                                   activebackground="#3a56d4", activeforeground=white,
                                   command=self.copy_url, cursor="hand2")
        self.btn_copy.pack(side="right")

        # ─── Big Action Button ───
        btn_frame = tk.Frame(self.root, bg=bg)
        btn_frame.pack(fill="x", padx=24, pady=12)

        self.btn_start = tk.Button(
            btn_frame, text="▶   S T A R T", font=("Segoe UI", 16, "bold"),
            bg=green, fg="#0f0f1a", relief="flat", pady=14,
            activebackground="#05c090", activeforeground="#0f0f1a",
            command=self.toggle_server, cursor="hand2"
        )
        self.btn_start.pack(fill="x")

        # ─── Log / Activity ───
        log_card = tk.Frame(self.root, bg=card_bg, padx=16, pady=12)
        log_card.pack(fill="x", padx=24, pady=(0, 8))

        tk.Label(log_card, text="ACTIVITY LOG", font=("Segoe UI", 9, "bold"),
                 bg=card_bg, fg=gray).pack(anchor="w", pady=(0, 6))

        self.log_text = tk.Text(log_card, font=("Consolas", 9), bg=dark_input, fg="#aaa",
                                 relief="flat", height=6, wrap="word", state="disabled",
                                 highlightthickness=1, highlightbackground="#333")
        self.log_text.pack(fill="x")

        # ─── Guide at bottom ───
        guide = tk.Frame(self.root, bg=bg)
        guide.pack(fill="x", padx=24, pady=(4, 12))

        steps_text = "① Click START  →  ② Copy URL  →  ③ Paste in Claude Connectors  →  ④ Chat! 🎉"
        tk.Label(guide, text=steps_text, font=("Segoe UI", 9), bg=bg, fg=gray,
                 wraplength=500).pack()

    def log(self, msg):
        """Add a message to the activity log."""
        self.log_text.config(state="normal")
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {msg}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def check_ready(self):
        """Check if required files exist."""
        if not SERVER_SCRIPT.exists():
            self.log("⚠ server.py not found!")
        if not CLOUDFLARED.exists():
            self.log("⚠ cloudflared.exe not found! Run setup.bat first.")
        else:
            self.log("✅ All files ready. Click START to begin.")

    def toggle_server(self):
        """Start or stop the server."""
        if self.is_running:
            self.stop_server()
        else:
            self.start_server()

    def start_server(self):
        """Start MCP server + Cloudflare tunnel."""
        self.btn_start.config(state="disabled", text="⏳  Starting...", bg="#555")
        self.log("Starting MCP server on port 8787...")
        threading.Thread(target=self._start_worker, daemon=True).start()

    def _start_worker(self):
        try:
            # 1) Find python executable
            if getattr(sys, 'frozen', False):
                # Running as .exe — find python in PATH or known locations
                python_exe = None
                for p in [
                    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python312", "python.exe"),
                    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python311", "python.exe"),
                    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python310", "python.exe"),
                ]:
                    if os.path.isfile(p):
                        python_exe = p
                        break
                if not python_exe:
                    import shutil
                    python_exe = shutil.which("python") or shutil.which("py") or "python"
            else:
                python_exe = sys.executable
                if "pythonw" in python_exe.lower():
                    python_exe = python_exe.lower().replace("pythonw", "python")

            # 2) Start MCP server
            self.server_proc = subprocess.Popen(
                [python_exe, str(SERVER_SCRIPT)],
                cwd=str(APP_DIR),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

            self.root.after(0, lambda: self.lbl_server.config(text="⬤  Running", fg="#06d6a0"))
            self.root.after(0, lambda: self.log("✅ MCP server started (PID: {})".format(self.server_proc.pid)))

            time.sleep(3)

            # Check server didn't crash
            if self.server_proc.poll() is not None:
                self.root.after(0, lambda: self.log("❌ Server crashed! Check server.py"))
                self.root.after(0, lambda: self.lbl_server.config(text="⬤  Error", fg="#ef476f"))
                self.root.after(0, lambda: self.btn_start.config(state="normal", text="▶   S T A R T", bg="#06d6a0"))
                return

            # 3) Start ngrok tunnel (permanent URL!)
            self.root.after(0, lambda: self.log("🌐 Connecting ngrok tunnel..."))

            # Find ngrok
            ngrok_exe = None
            for p in [
                str(APP_DIR / "ngrok.exe"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "ngrok", "ngrok.exe"),
            ]:
                if os.path.isfile(p):
                    ngrok_exe = p
                    break
            if not ngrok_exe:
                import shutil
                ngrok_exe = shutil.which("ngrok") or "ngrok"

            # Read ngrok domain from config
            try:
                with open(APP_DIR / "config.json", "r") as f:
                    _cfg = json.load(f)
                NGROK_DOMAIN = _cfg.get("ngrok_domain", "")
            except Exception:
                NGROK_DOMAIN = ""

            if not NGROK_DOMAIN:
                self.root.after(0, lambda: self.log("❌ Set ngrok_domain in config.json first!"))
                self.root.after(0, self._reset_ui)
                return

            self.tunnel_proc = subprocess.Popen(
                [ngrok_exe, "http", f"--url={NGROK_DOMAIN}", "8787"],
                cwd=str(APP_DIR),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

            # Wait for ngrok to connect (check its local API)
            time.sleep(5)

            if self.tunnel_proc.poll() is not None:
                self.root.after(0, lambda: self.log("❌ ngrok failed to start"))
                self.root.after(0, self._reset_ui)
                return

            self.tunnel_url = f"https://{NGROK_DOMAIN}/mcp"
            self.is_running = True
            self.root.after(0, self._on_connected)

            # Keep reading stdout to prevent buffer overflow
            if self.tunnel_proc and self.tunnel_proc.stdout:
                for _ in self.tunnel_proc.stdout:
                    pass

        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Error: {e}"))
            self.root.after(0, self._reset_ui)

    def _on_connected(self):
        """Called when tunnel URL is found."""
        self.url_var.set(self.tunnel_url)
        self.lbl_tunnel.config(text="⬤  Connected", fg="#06d6a0")
        self.btn_start.config(state="normal", text="⏹   S T O P", bg="#ef476f")
        self.log(f"🎉 CONNECTED! URL: {self.tunnel_url}")
        self.log("📋 Click Copy → Paste in Claude → Connectors → Add")

    def stop_server(self):
        """Stop everything."""
        self.log("Stopping server and tunnel...")

        if self.tunnel_proc:
            try:
                self.tunnel_proc.terminate()
                self.tunnel_proc.wait(timeout=5)
            except Exception:
                try:
                    self.tunnel_proc.kill()
                except Exception:
                    pass
            self.tunnel_proc = None

        if self.server_proc:
            try:
                self.server_proc.terminate()
                self.server_proc.wait(timeout=5)
            except Exception:
                try:
                    self.server_proc.kill()
                except Exception:
                    pass
            self.server_proc = None

        self.is_running = False
        self.tunnel_url = None
        self._reset_ui()
        self.log("⏹ Stopped. Click START to reconnect.")

    def _reset_ui(self):
        """Reset UI to initial state."""
        self.lbl_server.config(text="⬤  Offline", fg="#ef476f")
        self.lbl_tunnel.config(text="⬤  Offline", fg="#ef476f")
        self.url_var.set("Click START to get your URL...")
        self.btn_start.config(state="normal", text="▶   S T A R T", bg="#06d6a0")
        self.is_running = False

    def copy_url(self):
        """Copy tunnel URL to clipboard."""
        if self.tunnel_url:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.tunnel_url)
            self.btn_copy.config(text="✅ Copied!")
            self.log("📋 URL copied to clipboard!")
            self.root.after(2000, lambda: self.btn_copy.config(text="📋 Copy"))
        else:
            messagebox.showinfo("CloudLap", "Start the server first to get a URL!")

    def on_close(self):
        """Clean shutdown."""
        if self.is_running:
            if messagebox.askyesno("CloudLap", "Server is running. Stop and exit?"):
                self.stop_server()
                self.root.destroy()
        else:
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = CloudLapApp(root)
    root.mainloop()
