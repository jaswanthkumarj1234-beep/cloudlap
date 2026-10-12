#!/usr/bin/env python3
"""CloudLap for macOS: a small MCP server that lets Claude work on your Mac.

Locked by default. Unlock it with a 6-digit code from your authenticator app.
Listens on 127.0.0.1 only; reach it through an ngrok tunnel.

Usage:
    server.py            start the server
    server.py --setup    create the authenticator secret and show its QR code
    server.py --check N  check a 6-digit code against the secret
"""
import functools
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil
import pyotp

HOST = "127.0.0.1"
PORT = int(os.environ.get("CLOUDLAP_PORT", "8787"))
UNLOCK_MINUTES = max(1, int(os.environ.get("CLOUDLAP_UNLOCK_MINUTES", "10")))
UNLOCK_SECONDS = UNLOCK_MINUTES * 60
MAX_FAILURES = 3
MAX_READ_BYTES = 100 * 1024
CMD_TIMEOUT = 60
MAX_OUTPUT_CHARS = 20000

HOME = Path.home()
DATA_DIR = HOME / ".cloudlap"
CONTEXT_DIR = DATA_DIR / "contexts"
SECRET_FILE = DATA_DIR / "totp_secret.txt"
MEMORY_FILE = DATA_DIR / "memory.md"
AUDIT_FILE = DATA_DIR / "audit_log.jsonl"
for d in (DATA_DIR, CONTEXT_DIR):
    d.mkdir(exist_ok=True)
os.chmod(DATA_DIR, 0o700)

# A simple guard, not a sandbox. Anyone who unlocks the server can still do a lot.
BLOCKED_COMMANDS = [
    "sudo", "rm -rf /", "rm -rf ~", "mkfs", "dd if=", ":(){", "shutdown",
    "reboot", "diskutil erase", "diskutil partition", "launchctl unload",
    "chmod -r 777 /", "> /dev/sd", "> /dev/disk",
]

LOCKED_MSG = ("CloudLap is locked. Ask the owner for the current 6-digit code "
              "from their authenticator app, then call the `unlock` tool with it.")

_state = {"until": 0.0, "fails": 0, "blocked_until": 0.0, "last_step": -1}


def audit(event: str, detail: str = "") -> None:
    """Append one line per event. Never log codes or file contents."""
    try:
        with AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"t": datetime.now().isoformat(timespec="seconds"),
                                "event": event, "detail": detail[:300]}) + "\n")
        os.chmod(AUDIT_FILE, 0o600)
    except OSError:
        pass


def get_secret() -> str:
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text().strip()
    secret = pyotp.random_base32()
    SECRET_FILE.write_text(secret)
    os.chmod(SECRET_FILE, 0o600)
    return secret


def setup() -> None:
    secret = get_secret()
    uri = pyotp.TOTP(secret).provisioning_uri(name="CloudLap-Mac", issuer_name="CloudLap")
    print("\n=== CloudLap authenticator setup ===")
    print("Scan this with Google Authenticator, Microsoft Authenticator, Authy or 1Password:\n")
    try:
        import qrcode
        qr = qrcode.QRCode()
        qr.add_data(uri)
        qr.print_ascii(invert=True)
    except Exception:
        print("(QR code unavailable, enter the key below by hand)")
    print(f"\nManual key: {secret}")
    print(f"Saved at:   {SECRET_FILE}\n")


def check_code(code: str) -> bool:
    """True if the code is valid. Each code works once."""
    totp = pyotp.TOTP(get_secret())
    code = code.strip().replace(" ", "")
    now = time.time()
    for offset in (-1, 0, 1):
        t = now + offset * totp.interval
        if totp.at(t) == code:
            step = int(t // totp.interval)
            if step <= _state["last_step"]:
                return False
            _state["last_step"] = step
            return True
    return False


try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer
    mcp = MCPServer("Cloudlap")

    def serve() -> None:
        mcp.run(transport="streamable-http", host=HOST, port=PORT)
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP
    try:
        from mcp.server.transport_security import TransportSecuritySettings
        mcp = FastMCP("Cloudlap", host=HOST, port=PORT,
                      transport_security=TransportSecuritySettings(
                          enable_dns_rebinding_protection=False))
    except Exception:
        mcp = FastMCP("Cloudlap", host=HOST, port=PORT)

    def serve() -> None:
        mcp.run(transport="streamable-http")


def is_unlocked() -> bool:
    return time.time() < _state["until"]


def guarded(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not is_unlocked():
            return LOCKED_MSG
        return fn(*args, **kwargs)
    return wrapper


def resolve(path: str) -> Path:
    p = Path(path).expanduser() if path else HOME
    return p if p.is_absolute() else HOME / p


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


@mcp.tool()
def unlock(code: str) -> str:
    """Unlock the server with the 6-digit code from the owner's authenticator app."""
    now = time.time()
    if now < _state["blocked_until"]:
        return f"Too many failed attempts. Try again in {int(_state['blocked_until'] - now)}s."
    if check_code(code):
        _state["fails"] = 0
        _state["until"] = now + UNLOCK_SECONDS
        audit("unlock", f"{UNLOCK_MINUTES} min")
        return f"Unlocked for {UNLOCK_MINUTES} minutes."
    _state["fails"] += 1
    audit("unlock_failed")
    if _state["fails"] >= MAX_FAILURES:
        _state["blocked_until"] = now + 300
        _state["fails"] = 0
        return "Wrong code. Too many attempts: locked out for 5 minutes."
    return "Wrong code."


@mcp.tool()
def lock() -> str:
    """Lock the server again right away."""
    _state["until"] = 0.0
    audit("lock")
    return "Locked."


@mcp.tool()
def get_system_info() -> str:
    """Get system information: OS, hostname, Python version, CPU, RAM and disk."""
    vm = psutil.virtual_memory()
    du = shutil.disk_usage(str(HOME))
    return "\n".join([
        "=== System & OS ===",
        f"OS: macOS {platform.mac_ver()[0]} ({platform.platform()})",
        f"Architecture: {platform.machine()}",
        f"Hostname: {platform.node()}",
        f"Python: {sys.version.split()[0]} ({sys.executable})",
        "",
        "=== CPU ===",
        f"Logical Cores: {psutil.cpu_count()}  Physical: {psutil.cpu_count(logical=False)}",
        f"CPU Utilization: {psutil.cpu_percent(interval=0.5)}%",
        "",
        "=== Memory ===",
        f"Total: {human(vm.total)}  Available: {human(vm.available)}  Used: {vm.percent}%",
        "",
        "=== Storage (home volume) ===",
        f"Total: {human(du.total)}  Used: {human(du.used)}  Free: {human(du.free)}",
    ])


@mcp.tool()
@guarded
def list_directory(path: str = "") -> str:
    """List directory contents with sizes and modification times. Defaults to home."""
    p = resolve(path)
    if not p.is_dir():
        return f"Not a directory: {p}"
    audit("list_directory", str(p))
    rows = []
    for e in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        try:
            st = e.stat()
            kind = "DIR " if e.is_dir() else "FILE"
            size = "" if e.is_dir() else human(st.st_size)
            when = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
            rows.append(f"{kind} {e.name:<40} {size:>10}  {when}")
        except OSError:
            rows.append(f"???? {e.name}")
    return f"{p}\n" + "\n".join(rows)


@mcp.tool()
@guarded
def read_file(path: str) -> str:
    """Read a file's contents (up to 100KB, with a truncation warning)."""
    p = resolve(path)
    if not p.is_file():
        return f"Not a file: {p}"
    audit("read_file", str(p))
    data = p.read_bytes()
    text = data[:MAX_READ_BYTES].decode("utf-8", errors="replace")
    if len(data) > MAX_READ_BYTES:
        text += f"\n\n[TRUNCATED: showing first {MAX_READ_BYTES} of {len(data)} bytes]"
    return text


@mcp.tool()
@guarded
def write_file(path: str, content: str) -> str:
    """Write or overwrite a file, creating parent directories if needed."""
    p = resolve(path)
    audit("write_file", str(p))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to {p}"


@mcp.tool()
@guarded
def search_files(pattern: str, directory: str = "") -> str:
    """Search recursively for files matching a glob pattern (max 100 results)."""
    root = resolve(directory)
    audit("search_files", f"{pattern} in {root}")
    results = []
    try:
        for p in root.rglob(pattern):
            results.append(str(p))
            if len(results) >= 100:
                break
    except OSError as e:
        return f"Search error: {e}"
    return "\n".join(results) if results else "No matches."


@mcp.tool()
@guarded
def run_command(command: str) -> str:
    """Run a shell command (zsh) in the home directory with a 60s timeout."""
    low = command.lower()
    for bad in BLOCKED_COMMANDS:
        if bad in low:
            audit("run_command_blocked", command)
            return f"Blocked: command contains '{bad}'."
    audit("run_command", command)
    try:
        r = subprocess.run(command, shell=True, cwd=str(HOME), capture_output=True,
                           text=True, timeout=CMD_TIMEOUT, executable="/bin/zsh")
    except subprocess.TimeoutExpired:
        return f"Timed out after {CMD_TIMEOUT}s."
    out = (r.stdout or "") + (("\n[stderr]\n" + r.stderr) if r.stderr else "")
    if len(out) > MAX_OUTPUT_CHARS:
        out = out[:MAX_OUTPUT_CHARS] + "\n[OUTPUT TRUNCATED]"
    return f"[exit code {r.returncode}]\n{out}"


@mcp.tool()
@guarded
def save_context(summary: str, current_task: str = "", files_changed: str = "",
                 next_steps: str = "", project_name: str = "default") -> str:
    """Save the conversation context so a future session can pick up from it."""
    safe = "".join(c for c in project_name if c.isalnum() or c in "-_ ") or "default"
    data = {"summary": summary, "current_task": current_task,
            "files_changed": files_changed, "next_steps": next_steps,
            "saved_at": datetime.now().isoformat(timespec="seconds")}
    (CONTEXT_DIR / f"{safe}.json").write_text(json.dumps(data, indent=2))
    return f"Saved context for '{safe}'."


@mcp.tool()
@guarded
def load_context(project_name: str = "default") -> str:
    """Load saved context from a previous session."""
    safe = "".join(c for c in project_name if c.isalnum() or c in "-_ ") or "default"
    f = CONTEXT_DIR / f"{safe}.json"
    if not f.exists():
        return f"No saved context for '{safe}'."
    return f.read_text()


@mcp.tool()
@guarded
def list_projects() -> str:
    """List all projects that have saved context."""
    names = sorted(p.stem for p in CONTEXT_DIR.glob("*.json"))
    return "\n".join(names) if names else "No saved projects."


@mcp.tool()
@guarded
def append_memory(note: str) -> str:
    """Save a quick note to persistent memory."""
    with MEMORY_FILE.open("a", encoding="utf-8") as f:
        f.write(f"- {datetime.now():%Y-%m-%d %H:%M}: {note}\n")
    return "Noted."


if __name__ == "__main__":
    if "--setup" in sys.argv:
        setup()
    elif "--check" in sys.argv:
        i = sys.argv.index("--check")
        ok = i + 1 < len(sys.argv) and check_code(sys.argv[i + 1])
        print("valid" if ok else "invalid")
        sys.exit(0 if ok else 1)
    else:
        get_secret()
        print(f"CloudLap running on http://{HOST}:{PORT}/mcp "
              f"(locked until you unlock it; unlock lasts {UNLOCK_MINUTES} min)", flush=True)
        serve()
