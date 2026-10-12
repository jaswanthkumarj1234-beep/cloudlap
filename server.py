"""
Remote MCP Server for Claude
Allows Claude to connect to this machine over Remote MCP (Streamable HTTP)
to execute commands, read/write files, and inspect the system.
"""

import asyncio
import datetime
import json
import logging
import os
import platform
import re
import shutil
import sys
from pathlib import Path
from typing import List, Optional

# Optional psutil for richer hardware diagnostics
try:
    import psutil
except ImportError:
    psutil = None

from mcp.server.mcpserver import MCPServer

# ---------------------------------------------------------
# Configuration Setup
# ---------------------------------------------------------
CONFIG_PATH = Path(__file__).parent / "config.json"
DEFAULT_CONFIG = {
    "port": 8787,
    "auth_token": "CHANGE_THIS_TO_A_STRONG_SECRET",
    "timeout_seconds": 120,
    "max_output_chars": 4000,
    "allowed_directories": ["~"],
    "log_file": "server.log",
}

config = DEFAULT_CONFIG.copy()
if CONFIG_PATH.exists():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            config.update(user_config)
    except Exception as e:
        print(f"Warning: Failed to load config.json, using defaults: {e}", file=sys.stderr)

# Setup logging
log_file = config.get("log_file", "server.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("claude-laptop-server")

# ---------------------------------------------------------
# Security Blocklist
# ---------------------------------------------------------
BLOCKED_PATTERNS = [
    r'\brm\s+-\w*r\w*\s+(/|~|\*|\.\.)',
    r'\bdel\b.*\s/[sq]',
    r'\brmdir\b.*\s/s',
    r'Remove-Item.*-Recurse.*[/\\](Windows|Program)',
    r'\bformat\s+[a-z]:',
    r'(curl|wget|iwr|Invoke-WebRequest)[^|]*\|\s*(sh|bash|iex|Invoke-Expression)',
    r'\b(iex|Invoke-Expression)\b',
    r'-(enc|encodedcommand)\b',
    r'\breg\s+(add|delete)',
    r'\b(shutdown|mkfs|sudo|netsh|schtasks|diskpart|bcdedit)\b',
    r'\bnet\s+(user|localgroup)',
    r'\.ssh|id_rsa|\.aws|\.npmrc|\.git-credentials|\.env\b',
]

compiled_blocked_patterns = [
    re.compile(p, re.IGNORECASE) for p in BLOCKED_PATTERNS
]


def check_command_security(command: str) -> Optional[str]:
    """Check if command matches any dangerous blocked pattern."""
    for pattern in compiled_blocked_patterns:
        if pattern.search(command):
            audit_log("run_command", {"command": command}, "BLOCKED", f"Matched: {pattern.pattern}")
            return f"Security Refusal: Command matched blocked safety rule: {pattern.pattern}"
    return None


def format_bytes(size: int) -> str:
    """Format bytes into human readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:3.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


# ---------------------------------------------------------
# Audit Log — every tool call is logged (OpenClaw's #1 flaw)
# ---------------------------------------------------------
AUDIT_LOG_PATH = Path(__file__).resolve().parent / "audit_log.jsonl"


def audit_log(tool_name: str, args: dict, status: str, detail: str = ""):
    """Append a structured audit entry for every tool call."""
    entry = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "tool": tool_name,
        "args": {k: (v[:200] if isinstance(v, str) else v) for k, v in args.items()},
        "status": status,
        "detail": detail[:500] if detail else "",
    }
    try:
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # never let audit logging break the server
    _activity(tool_name, args, status)


# ---------------------------------------------------------
# Activity log - tiny, automatic, self-trimming (for context hand-off)
# ---------------------------------------------------------
ACTIVITY_LOG_PATH = Path(__file__).resolve().parent / "memory" / "activity_log.md"
ACTIVITY_MAX_LINES = 200
_ACTION_RE = re.compile(
    r"(?i)\b(start|taskkill|stop-process|remove-item|del|rd|rmdir|set-content|add-content|"
    r"copy-item|copy|move-item|move|rename|new-item|mkdir|pip|npm|winget|python|pythonw|"
    r"explorer|set-clipboard|out-file|git)\b"
)


def _activity(tool_name: str, args: dict, status: str):
    """Append one short line for state-changing actions only. Never raises."""
    try:
        if status != "OK":
            return
        if tool_name == "write_file":
            text = "write_file: " + str(args.get("path", ""))
        elif tool_name == "run_command":
            cmd = " ".join(str(args.get("command", "")).split())
            if not _ACTION_RE.search(cmd):
                return
            text = "run_command: " + cmd
        else:
            return
        line = datetime.datetime.now().strftime("%m-%d %H:%M") + " " + text[:120]
        ACTIVITY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        if ACTIVITY_LOG_PATH.exists():
            lines = ACTIVITY_LOG_PATH.read_text(encoding="utf-8").splitlines()
        lines.append(line)
        ACTIVITY_LOG_PATH.write_text("\n".join(lines[-ACTIVITY_MAX_LINES:]) + "\n", encoding="utf-8")
    except Exception:
        pass  # never let activity logging break the server


def _activity_section(n: int = 20) -> str:
    """Last n activity lines, formatted for load_context output."""
    try:
        if not ACTIVITY_LOG_PATH.exists():
            return ""
        lines = ACTIVITY_LOG_PATH.read_text(encoding="utf-8").splitlines()[-n:]
        if not lines:
            return ""
        return "\n\n## Recent Activity (auto-logged, newest last)\n" + "\n".join(lines)
    except Exception:
        return ""


# ---------------------------------------------------------
# Rate Limiter — prevent abuse (OpenClaw's #2 flaw)
# ---------------------------------------------------------
# ---------------------------------------------------------
# Session nudge - remind the model that saved context exists
# ---------------------------------------------------------
import functools as _functools
import time as _nudge_time

NUDGE_IDLE_SECONDS = 30 * 60  # a gap this long is treated as a new session
_last_tool_call: Optional[float] = None


def _saved_project_names() -> list:
    try:
        mem = Path(__file__).resolve().parent / "memory"
        return sorted(p.stem[len("context_"):] for p in mem.glob("context_*.md"))
    except Exception:
        return []


def _nudge_text(tool_name: str) -> str:
    """One-off reminder on the first tool call of a new session, else ''. Never raises."""
    global _last_tool_call
    try:
        now = _nudge_time.time()
        first = _last_tool_call is None or (now - _last_tool_call) > NUDGE_IDLE_SECONDS
        _last_tool_call = now
        if tool_name in ("load_context", "save_context") or not first:
            return ""
        names = _saved_project_names()
        if not names:
            return ""
        return (
            "\n\n[CloudLap] New session detected. Saved context exists for: "
            + ", ".join(names)
            + ". Call load_context(project_name='...') (try 'default' first) "
            "to restore previous work before continuing."
        )
    except Exception:
        return ""


def _nudged(fn):
    """Decorator: append the session nudge to a tool's string result."""
    @_functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        result = await fn(*args, **kwargs)
        if isinstance(result, str):
            result += _nudge_text(fn.__name__)
        return result
    return wrapper


_rate_log: list[float] = []
RATE_LIMIT = 30  # max calls per minute


def check_rate_limit() -> Optional[str]:
    """Return error string if rate limit exceeded, else None."""
    import time as _time
    now = _time.time()
    _rate_log[:] = [t for t in _rate_log if now - t < 60]
    if len(_rate_log) >= RATE_LIMIT:
        audit_log("rate_limit", {}, "BLOCKED", f"{len(_rate_log)} calls in last 60s")
        return f"Rate limit exceeded: {RATE_LIMIT} calls/minute. Wait a moment."
    _rate_log.append(now)
    return None


# ---------------------------------------------------------
# Directory Sandbox — restrict file access (OpenClaw's #3 flaw)
# ---------------------------------------------------------
def check_path_allowed(file_path: str) -> Optional[str]:
    """Check if a path is within the allowed directories from config."""
    allowed = config.get("allowed_directories", ["~"])
    resolved = Path(os.path.expanduser(file_path)).resolve()

    # Always block sensitive files regardless of allowed_directories
    sensitive = [".ssh", "id_rsa", ".aws", ".npmrc", ".git-credentials",
                 ".env", "credentials", "secrets", "tokens"]
    path_str = str(resolved).lower()
    for s in sensitive:
        if s.lower() in path_str:
            audit_log("path_check", {"path": file_path}, "BLOCKED", f"Sensitive path: {s}")
            return f"Security Refusal: Access to sensitive path blocked ({s})"

    # If allowed_directories is ["~"], allow anything under home
    for allowed_dir in allowed:
        allowed_resolved = Path(os.path.expanduser(allowed_dir)).resolve()
        try:
            resolved.relative_to(allowed_resolved)
            return None  # path is within allowed directory
        except ValueError:
            continue

    audit_log("path_check", {"path": file_path}, "BLOCKED", "Outside allowed directories")
    return f"Security Refusal: Path '{file_path}' is outside allowed directories: {allowed}"


# ---------------------------------------------------------
# FastMCP Server Initialization
# ---------------------------------------------------------
server_port = int(config.get("port", 8787))

# Build dynamic instructions that tell Claude about saved context
_instructions_parts = [
    "You are connected to the user's laptop via CloudLap.",
    "You have tools to run commands, read/write files, search, and get system info.",
    "",
    "IMPORTANT: This server has a persistent memory system.",
    "At the START of every conversation, call `load_context()` to check for saved context from previous sessions.",
    "Before the user leaves, ask if they want to save context with `save_context()`.",
    "Use `append_memory()` to remember important preferences or decisions.",
]

# Check if there are saved contexts and tell Claude about them
_memory_dir = Path(__file__).resolve().parent / "memory"
if _memory_dir.exists():
    _contexts = list(_memory_dir.glob("context_*.md"))
    if _contexts:
        _names = [f.stem.replace("context_", "") for f in _contexts]
        _instructions_parts.append("")
        _instructions_parts.append(f"SAVED PROJECTS FOUND: {', '.join(_names)}")
        _instructions_parts.append("Call `load_context()` now to restore the previous session!")

_instructions = "\n".join(_instructions_parts)

mcp = MCPServer("CloudLap", instructions=_instructions)


@mcp.tool()
@_nudged
async def run_command(command: str, cwd: str = "") -> str:
    """Execute a shell command with security validation and timeout.

    Args:
        command: Shell command string to execute.
        cwd: Working directory (optional, defaults to user home directory).

    Returns:
        Exit code, stdout, and stderr output (last 4000 characters).
    """
    logger.info("Executing command: %s (cwd: %s)", command, cwd or "HOME")

    # 0. Rate Limit
    rate_error = check_rate_limit()
    if rate_error:
        return rate_error

    # 1. Security Check
    security_error = check_command_security(command)
    if security_error:
        logger.warning("Blocked dangerous command: %s", command)
        return security_error

    # 2. Resolve Working Directory
    if not cwd or cwd.strip() == "":
        work_dir = Path.home()
    else:
        work_dir = Path(os.path.expanduser(cwd)).resolve()

    if not work_dir.exists():
        return f"Error: Working directory does not exist: {work_dir}"
    if not work_dir.is_dir():
        return f"Error: Working directory path is not a directory: {work_dir}"

    timeout_seconds = int(config.get("timeout_seconds", 120))
    max_chars = int(config.get("max_output_chars", 4000))

    try:
        # Determine shell based on OS
        if platform.system() == "Windows":
            # Use PowerShell or cmd
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=str(work_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=str(work_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return f"Error: Command timed out after {timeout_seconds} seconds."
    except Exception as e:
        logger.exception("Subprocess execution failed")
        return f"Error executing command: {str(e)}"

    stdout_text = stdout_bytes.decode("utf-8", errors="replace")
    stderr_text = stderr_bytes.decode("utf-8", errors="replace")
    returncode = proc.returncode

    # Truncate to last max_output_chars if output exceeds limit
    if len(stdout_text) > max_chars:
        stdout_truncated = (
            f"[... truncated earlier output, showing last {max_chars} chars ...]\n"
            + stdout_text[-max_chars:]
        )
    else:
        stdout_truncated = stdout_text

    if len(stderr_text) > max_chars:
        stderr_truncated = (
            f"[... truncated earlier output, showing last {max_chars} chars ...]\n"
            + stderr_text[-max_chars:]
        )
    else:
        stderr_truncated = stderr_text

    result_parts = [f"Exit Code: {returncode}"]
    if stdout_truncated:
        result_parts.append(f"STDOUT:\n{stdout_truncated.strip()}")
    if stderr_truncated:
        result_parts.append(f"STDERR:\n{stderr_truncated.strip()}")
    if not stdout_truncated and not stderr_truncated:
        result_parts.append("(Command produced no output)")

    audit_log("run_command", {"command": command, "cwd": cwd}, "OK", f"exit={returncode}")
    return "\n\n".join(result_parts)


@mcp.tool()
@_nudged
async def read_file(path: str) -> str:
    """Read a file's contents up to 100KB with truncation warning.

    Args:
        path: Path to the file to read.

    Returns:
        The content of the file.
    """
    logger.info("Reading file: %s", path)

    rate_error = check_rate_limit()
    if rate_error:
        return rate_error

    path_error = check_path_allowed(path)
    if path_error:
        return path_error

    file_path = Path(os.path.expanduser(path)).resolve()
    audit_log("read_file", {"path": str(file_path)}, "OK")

    if not file_path.exists():
        return f"Error: File does not exist: {file_path}"
    if not file_path.is_file():
        return f"Error: Path is not a file: {file_path}"

    max_bytes = 100 * 1024  # 100 KB
    try:
        file_size = file_path.stat().st_size
        with open(file_path, "rb") as f:
            data = f.read(max_bytes)

        text = data.decode("utf-8", errors="replace")
        if file_size > max_bytes:
            warning = (
                f"\n\n[Warning: File size ({format_bytes(file_size)}) exceeds 100KB limit. "
                f"Showing first {format_bytes(max_bytes)} only.]"
            )
            return text + warning

        return text
    except Exception as e:
        logger.exception("Failed to read file: %s", path)
        return f"Error reading file: {str(e)}"


@mcp.tool()
@_nudged
async def write_file(path: str, content: str) -> str:
    """Write or overwrite a file with given content, creating parent directories if needed.

    Args:
        path: Destination file path.
        content: String content to write.

    Returns:
        Confirmation message with path and size written.
    """
    logger.info("Writing file: %s", path)

    rate_error = check_rate_limit()
    if rate_error:
        return rate_error

    path_error = check_path_allowed(path)
    if path_error:
        return path_error

    file_path = Path(os.path.expanduser(path)).resolve()
    audit_log("write_file", {"path": str(file_path), "size": len(content)}, "OK")

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        encoded = content.encode("utf-8")
        with open(file_path, "wb") as f:
            f.write(encoded)

        return (
            f"Successfully wrote {format_bytes(len(encoded))} ({len(encoded)} bytes) "
            f"to {file_path}"
        )
    except Exception as e:
        logger.exception("Failed to write file: %s", path)
        return f"Error writing file: {str(e)}"


@mcp.tool()
@_nudged
async def list_directory(path: str = "") -> str:
    """List directory contents with sizes and modification timestamps.

    Args:
        path: Directory path (optional, defaults to user home directory).

    Returns:
        Formatted listing of directory entries.
    """
    if not path or path.strip() == "":
        dir_path = Path.home()
    else:
        dir_path = Path(os.path.expanduser(path)).resolve()

    logger.info("Listing directory: %s", dir_path)

    if not dir_path.exists():
        return f"Error: Directory does not exist: {dir_path}"
    if not dir_path.is_dir():
        return f"Error: Path is not a directory: {dir_path}"

    try:
        entries = []
        for entry in os.scandir(dir_path):
            try:
                stat_res = entry.stat()
                mtime = datetime.datetime.fromtimestamp(
                    stat_res.st_mtime
                ).strftime("%Y-%m-%d %H:%M:%S")
                if entry.is_dir():
                    kind = "[DIR] "
                    size_str = "<DIR>"
                else:
                    kind = "[FILE]"
                    size_str = format_bytes(stat_res.st_size)
                entries.append((kind, size_str, mtime, entry.name))
            except PermissionError:
                entries.append(("[???] ", "N/A", "N/A", f"{entry.name} (Access Denied)"))
            except Exception:
                continue

        # Sort: directories first, then alphabetical
        entries.sort(key=lambda x: (0 if x[0] == "[DIR] " else 1, x[3].lower()))

        lines = [f"Directory listing of {dir_path}:", "-" * 70]
        lines.append(f"{'Type':<8} {'Size':<12} {'Modified':<20} {'Name'}")
        lines.append("-" * 70)

        for kind, size_str, mtime, name in entries:
            lines.append(f"{kind:<8} {size_str:<12} {mtime:<20} {name}")

        lines.append("-" * 70)
        lines.append(f"Total entries: {len(entries)}")
        return "\n".join(lines)
    except Exception as e:
        logger.exception("Failed to list directory: %s", dir_path)
        return f"Error listing directory: {str(e)}"


@mcp.tool()
@_nudged
async def search_files(pattern: str, directory: str = "") -> str:
    """Search for files matching a glob pattern recursively.

    Args:
        pattern: Glob pattern to search (e.g. '*.py', '*config*', '*.txt').
        directory: Root search directory (optional, defaults to user home directory).

    Returns:
        List of matching file paths (max 100 results).
    """
    if not directory or directory.strip() == "":
        search_root = Path.home()
    else:
        search_root = Path(os.path.expanduser(directory)).resolve()

    logger.info("Searching for '%s' in %s", pattern, search_root)

    if not search_root.exists() or not search_root.is_dir():
        return f"Error: Invalid search root directory: {search_root}"

    matches: List[str] = []
    max_results = 100

    def recursive_search(curr_path: Path):
        try:
            # Check matching items in curr_path
            for p in curr_path.glob(pattern):
                matches.append(str(p))
                if len(matches) >= max_results:
                    return

            # Traverse subdirectories safely
            for child in curr_path.iterdir():
                if len(matches) >= max_results:
                    return
                # Skip hidden directories and large vendor/cache folders
                if child.is_dir() and not child.is_symlink():
                    if child.name.startswith(".") or child.name in {
                        "node_modules",
                        "__pycache__",
                        "venv",
                        ".venv",
                        "$Recycle.Bin",
                    }:
                        continue
                    recursive_search(child)
        except (PermissionError, OSError):
            pass

    recursive_search(search_root)

    if not matches:
        return f"No files matching '{pattern}' found under {search_root}"

    lines = [f"Found {len(matches)} match(es) for '{pattern}' in {search_root}:"]
    for m in matches:
        lines.append(f"  - {m}")

    if len(matches) >= max_results:
        lines.append(f"\n(Search capped at {max_results} results)")

    return "\n".join(lines)


@mcp.tool()
@_nudged
async def get_system_info() -> str:
    """Get system information including OS, hostname, Python version, CPU, RAM, and disk usage.

    Returns:
        Structured system information.
    """
    logger.info("Fetching system info")
    info = []

    # OS & Host
    info.append("=== System & OS ===")
    info.append(f"OS: {platform.system()} {platform.release()} ({platform.version()})")
    info.append(f"Architecture: {platform.machine()} ({platform.architecture()[0]})")
    info.append(f"Hostname: {platform.node()}")
    info.append(f"Platform: {platform.platform()}")
    info.append(f"Python Version: {platform.python_version()} ({sys.executable})")

    # CPU
    info.append("\n=== CPU ===")
    cpu_count = os.cpu_count() or 1
    info.append(f"Logical Cores: {cpu_count}")
    if psutil:
        try:
            info.append(f"Physical Cores: {psutil.cpu_count(logical=False)}")
            info.append(f"CPU Utilization: {psutil.cpu_percent(interval=0.1)}%")
        except Exception:
            pass

    # RAM
    info.append("\n=== Memory (RAM) ===")
    if psutil:
        try:
            mem = psutil.virtual_memory()
            info.append(f"Total: {format_bytes(mem.total)}")
            info.append(f"Available: {format_bytes(mem.available)}")
            info.append(f"Used: {format_bytes(mem.used)} ({mem.percent}%)")
        except Exception as e:
            info.append(f"Memory query error: {e}")
    else:
        # Windows fallback via ctypes
        if platform.system() == "Windows":
            try:
                import ctypes

                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                info.append(f"Total: {format_bytes(stat.ullTotalPhys)}")
                info.append(f"Available: {format_bytes(stat.ullAvailPhys)}")
                info.append(f"Memory Load: {stat.dwMemoryLoad}%")
            except Exception as e:
                info.append(f"Memory info unavailable: {e}")
        else:
            info.append("Memory: psutil not installed")

    # Disk
    info.append("\n=== Storage (Disks) ===")
    try:
        home_path = Path.home()
        disk_usage = shutil.disk_usage(str(home_path))
        info.append(f"Home Drive ({home_path.anchor}):")
        info.append(f"  Total: {format_bytes(disk_usage.total)}")
        info.append(f"  Used:  {format_bytes(disk_usage.used)}")
        info.append(f"  Free:  {format_bytes(disk_usage.free)}")
        percent_used = (disk_usage.used / disk_usage.total) * 100
        info.append(f"  Usage: {percent_used:.1f}%")
    except Exception as e:
        info.append(f"Disk query error: {e}")

    return "\n".join(info)


# ---------------------------------------------------------
# Persistent Context / Memory System
# ---------------------------------------------------------
MEMORY_DIR = Path(__file__).resolve().parent / "memory"
CONTEXT_FILE = MEMORY_DIR / "context.md"
MEMORY_LOG = MEMORY_DIR / "memory_log.md"
PROJECTS_FILE = MEMORY_DIR / "projects.md"


@mcp.tool()
async def save_context(
    summary: str,
    current_task: str = "",
    files_changed: str = "",
    next_steps: str = "",
    project_name: str = "default",
) -> str:
    """Save the current conversation context so it can be loaded in a future session.
    Call this before the user switches accounts or ends a session.

    Args:
        summary: A detailed summary of what was discussed and accomplished in this session.
        current_task: What the user is currently working on (overall goal).
        files_changed: List of files that were created, modified, or deleted.
        next_steps: What should be done next when the user returns.
        project_name: Name of the project being worked on (default: "default").
    """
    logger.info("Saving context for project: %s", project_name)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().isoformat(timespec="seconds")

    context = f"""# CloudLap Context — {project_name}
_Last updated: {timestamp}_

## Current Task
{current_task or "Not specified"}

## Session Summary
{summary}

## Files Changed
{files_changed or "None recorded"}

## Next Steps
{next_steps or "None specified"}
"""

    # Save main context (overwrite with latest)
    project_context = MEMORY_DIR / f"context_{project_name}.md"
    project_context.write_text(context, encoding="utf-8")

    # Also append to the running log (never overwrites)
    with open(MEMORY_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n---\n## Session — {timestamp} — {project_name}\n")
        f.write(f"{summary}\n")
        if files_changed:
            f.write(f"\nFiles: {files_changed}\n")
        if next_steps:
            f.write(f"\nNext: {next_steps}\n")

    return (
        f"✅ Context saved for project '{project_name}'!\n"
        f"File: {project_context}\n\n"
        f"When you start a new session (any account), just say:\n"
        f'"Load my context for {project_name}"'
    )


@mcp.tool()
async def load_context(project_name: str = "default") -> str:
    """Load the saved context from a previous session. Use this at the start of a new
    session to restore full context about what was previously done.

    Args:
        project_name: Name of the project to load context for (default: "default").
    """
    logger.info("Loading context for project: %s", project_name)

    project_context = MEMORY_DIR / f"context_{project_name}.md"

    if not project_context.exists():
        # Try to find any context files
        available = list(MEMORY_DIR.glob("context_*.md")) if MEMORY_DIR.exists() else []
        if available:
            names = [f.stem.replace("context_", "") for f in available]
            return (
                f"No context found for project '{project_name}'.\n"
                f"Available projects: {', '.join(names)}\n"
                f"Try: load_context(project_name='...')" + _activity_section()
            )
        return "No saved context found. This appears to be a fresh start!" + _activity_section()

    context = project_context.read_text(encoding="utf-8")

    # Also load recent memory log entries
    recent_log = ""
    if MEMORY_LOG.exists():
        log_content = MEMORY_LOG.read_text(encoding="utf-8")
        # Get last 3000 chars of log
        if len(log_content) > 3000:
            recent_log = "\n\n## Recent Session History\n" + log_content[-3000:]
        else:
            recent_log = "\n\n## Full Session History\n" + log_content

    return context + recent_log + _activity_section()


@mcp.tool()
async def append_memory(note: str, category: str = "general") -> str:
    """Save a quick note or piece of information to persistent memory.
    Use this to remember user preferences, important decisions, or anything
    that should persist across sessions.

    Args:
        note: The information to remember.
        category: Category for the note (e.g., "preference", "decision", "todo", "general").
    """
    logger.info("Appending memory: [%s] %s", category, note[:50])
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"- [{timestamp}] **[{category}]** {note}\n"

    notes_file = MEMORY_DIR / "notes.md"
    if not notes_file.exists():
        notes_file.write_text("# CloudLap Memory Notes\n\n", encoding="utf-8")

    with open(notes_file, "a", encoding="utf-8") as f:
        f.write(entry)

    return f"✅ Remembered: [{category}] {note}"


@mcp.tool()
@_nudged
async def list_projects() -> str:
    """List all projects that have saved context."""
    logger.info("Listing projects with saved context")

    if not MEMORY_DIR.exists():
        return "No projects found. No context has been saved yet."

    contexts = list(MEMORY_DIR.glob("context_*.md"))
    if not contexts:
        return "No projects found."

    lines = ["# Saved Projects\n"]
    for ctx in sorted(contexts):
        name = ctx.stem.replace("context_", "")
        stat = ctx.stat()
        mod_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        size = format_bytes(stat.st_size)
        lines.append(f"- **{name}** — last updated: {mod_time} ({size})")

    # Also check for notes
    notes_file = MEMORY_DIR / "notes.md"
    if notes_file.exists():
        lines.append(f"\n📝 Memory notes: {format_bytes(notes_file.stat().st_size)}")

    if MEMORY_LOG.exists():
        lines.append(f"📋 Session log: {format_bytes(MEMORY_LOG.stat().st_size)}")

    return "\n".join(lines)


# ---------------------------------------------------------
# Server Execution
# ---------------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting Remote MCP Server on 0.0.0.0:%d (streamable-http)...", server_port)
    mcp.run(transport="streamable-http", host="0.0.0.0", port=server_port)

