<div align="center">

# CloudLap

**Turn your laptop into a personal cloud. Connect Claude AI from anywhere.**

[![CI](https://github.com/jaswanthkumarj1234-beep/cloudlap/actions/workflows/ci.yml/badge.svg)](https://github.com/jaswanthkumarj1234-beep/cloudlap/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![MCP Compatible](https://img.shields.io/badge/MCP-compatible-8B5CF6)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/license-MIT-22C55E)](LICENSE)
[![Tests: 26 passed](https://img.shields.io/badge/tests-26_passed-22C55E)](tests/)

Free · No API keys · Works from any device · Your data never leaves your machine

<br>

[Quick Start](#quick-start) · [How It Works](#how-it-works) · [Features](#features) · [Security](#security) · [Contributing](#contributing)

</div>

---

## What is CloudLap?

CloudLap is a self-hosted [MCP](https://modelcontextprotocol.io) server that gives Claude AI secure, remote access to your laptop. Once connected, Claude can run commands, read and write files, search your filesystem, and monitor system resources — all from any device with a browser.

It replaces paid tools like Cowork, Replit, and GitHub Codespaces with something that runs on your own hardware, costs nothing, and keeps your data on your machine.

```
  Any device (browser)               Your laptop (home/office)
 ┌────────────────────────┐         ┌────────────────────────┐
 │  Claude AI              │────────│  CloudLap Server        │
 │                         │  MCP   │                         │
 │  "Build a React app"    │◄───────│  → executes commands    │
 │  "Fix the test on L42"  │        │  → reads/writes files   │
 │  "Check disk usage"     │        │  → returns results      │
 └────────────────────────┘         └────────────────────────┘
```

## Features

**Core tools** — 10 MCP tools Claude can call on your machine:

| Tool | Description |
|------|-------------|
| `run_command` | Execute shell commands with security validation and 120s timeout |
| `read_file` | Read file contents (up to 100KB, with truncation warning) |
| `write_file` | Create or overwrite files, auto-creating parent directories |
| `list_directory` | List directory contents with file sizes and timestamps |
| `search_files` | Recursive glob search across your filesystem |
| `get_system_info` | CPU, RAM, disk, OS, hostname, battery status |
| `save_context` | Persist session state for later retrieval |
| `load_context` | Restore context from a previous session |
| `append_memory` | Store persistent notes and preferences |
| `list_projects` | List all saved project contexts |

**Security** — built-in protections at every layer:

- Command blocklist with 12+ regex patterns (blocks `rm -rf`, `format`, `shutdown`, registry edits, encoded commands, credential access)
- Directory sandbox via configurable `allowed_directories`
- Sensitive path blocking (`.ssh`, `.env`, `.aws`, `.git-credentials` — always denied)
- Rate limiting at 30 calls/minute
- Full audit log to `audit_log.jsonl` (every tool call with timestamp, args, status)
- 120-second command timeout

**Persistent memory** — context that survives across sessions and accounts:

When Claude connects, the server sends instructions listing any saved project contexts. Claude automatically loads previous session state without being asked. This means you can hit the free-tier limit on one account, switch to another, and continue exactly where you left off.

## Quick Start

### Easy setup (recommended)

1. Install [Python 3.10+](https://python.org/downloads) and tick **Add Python to PATH**.
2. Click **Code > Download ZIP** on this page, unzip it, and double-click **`setup.bat`**.
3. Answer the questions. The wizard installs everything, shows a QR code to scan with an authenticator app,
   sets up ngrok, starts CloudLap, and prints the address to paste into Claude.

You will need a phone with an authenticator app (Google or Microsoft Authenticator) and a free
[ngrok](https://ngrok.com) account. Full walkthrough: [SETUP.md](SETUP.md).

**Each time you use it:** open your authenticator app and tell Claude
"Connect to CloudLap, code is 123456" (the real 6-digit code). Every tool except `get_system_info`
stays locked until then. Say "lock CloudLap" when you finish.

### Manual setup (advanced)

Prefer to do it yourself? Follow these steps, and run `python totp_setup.py --show-qr` before you start the server.

### Prerequisites

- Windows 10 or 11 (macOS and Linux support planned)
- Python 3.10 or later — [download](https://python.org/downloads) (check "Add to PATH")
- Free ngrok account — [sign up](https://dashboard.ngrok.com/signup)

### Installation

```bash
git clone https://github.com/jaswanthkumarj1234-beep/cloudlap.git
cd cloudlap
pip install -r requirements.txt
```

### Configuration

```bash
copy config.example.json config.json
```

Edit `config.json` and add your [ngrok static domain](https://dashboard.ngrok.com/domains):

```json
{
  "port": 8787,
  "timeout_seconds": 120,
  "max_output_chars": 4000,
  "allowed_directories": ["~"],
  "log_file": "server.log",
  "ngrok_domain": "your-domain.ngrok-free.dev"
}
```

### ngrok setup (one time)

```bash
winget install ngrok.ngrok
ngrok config add-authtoken YOUR_TOKEN
```

Claim your free static domain at [dashboard.ngrok.com/domains](https://dashboard.ngrok.com/domains).

### Running

**GUI mode:**

```bash
python launcher.pyw
```

Click **Start CloudLap**. The window shows live status for the server, tunnel and authenticator lock,
warns you if setup is incomplete, copies your connector address, and can start CloudLap at sign-in.

**CLI mode:**

```bash
# Terminal 1
python server.py

# Terminal 2
ngrok http --url=your-domain.ngrok-free.dev 127.0.0.1:8787
```

### Connecting Claude

1. Open [claude.ai](https://claude.ai) or the Claude mobile app
2. Go to **Settings → Connectors → Add Custom Connector**
3. Name: `CloudLap`
4. URL: `https://your-domain.ngrok-free.dev/mcp`
5. Save, then unlock it in chat with a fresh authenticator code (see above)

## How It Works

CloudLap runs a Python server that implements the [Model Context Protocol](https://modelcontextprotocol.io) over Streamable HTTP. The server exposes tools that Claude can call through its built-in connector system.

[ngrok](https://ngrok.com) creates a persistent HTTPS tunnel from a static public URL to your local server, so Claude can reach your laptop from anywhere without opening ports or changing firewall rules.

```
Claude (Anthropic) → ngrok (HTTPS tunnel) → localhost:8787 → CloudLap (MCP server) → your filesystem
```

The server binds to `0.0.0.0:8787` locally. ngrok forwards to `127.0.0.1:8787` to avoid IPv6 issues on Windows.

## Security

CloudLap gives an AI agent direct access to your machine. That's powerful but inherently risky. The security model is defense-in-depth:

| Layer | Protection |
|-------|-----------|
| Command filtering | Regex blocklist rejects dangerous patterns before execution |
| Path sandboxing | File operations restricted to `allowed_directories` |
| Sensitive paths | `.ssh`, `.env`, `.aws`, credentials files blocked regardless of sandbox config |
| Rate limiting | 30 tool calls per minute, excess rejected |
| Two-factor unlock | Tools locked until the owner enters an authenticator code; unlock expires after `unlock_minutes` |
| Audit trail | Every tool call logged with timestamp, arguments, and result status |
| Timeouts | Commands killed after 120 seconds |
| No plugins | No extension system — no attack surface for malicious third-party code |
| Encryption | All traffic encrypted via ngrok's TLS termination |

> **Important:** Run `python totp_setup.py --show-qr` once and scan the QR code with an authenticator app. Until you do, the endpoint has no authentication and anyone with your ngrok URL has full access. With it set up, every tool except `get_system_info` stays locked until you call `unlock` with a fresh 6-digit code. Keep the URL private as well. See [SETUP.md](SETUP.md) for the full step-by-step guide.

See [SECURITY.md](SECURITY.md) for vulnerability reporting and hardening recommendations.

## Comparison

| | Cowork | Replit | GitHub Codespaces | CloudLap |
|---|:---:|:---:|:---:|:---:|
| AI + code execution | Yes | Yes | Yes | Yes |
| Mobile access | No | Yes | Yes | Yes |
| Runs on your hardware | Yes | No | No | Yes |
| Persistent memory | No | No | No | Yes |
| Cross-account context | No | No | No | Yes |
| Audit logging | No | No | Yes | Yes |
| Cost | \$20/mo | \$25/mo | Variable | Free |

## Project Structure

```
cloudlap/
├── server.py              MCP server with 10 tools
├── launcher.pyw           Desktop window (status, start/stop, copy address)
├── config.example.json    Configuration template
├── requirements.txt       Python dependencies
├── setup.bat              Windows installer script
├── start.bat              CLI launcher script
├── tests/
│   └── test_server.py     26 unit tests
├── .github/
│   ├── workflows/ci.yml   CI pipeline
│   └── ISSUE_TEMPLATE/    Bug and feature templates
├── CONTRIBUTING.md        Contribution guidelines
├── SECURITY.md            Security policy
├── CHANGELOG.md           Version history
└── LICENSE                MIT
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and guidelines.

Areas where help is needed:

- macOS and Linux support
- Docker containerized deployment
- Web-based dashboard UI
- OAuth / token authentication
- Multi-machine management

## License

MIT. See [LICENSE](LICENSE).

---

<div align="center">

If this project is useful to you, consider giving it a star. It helps others find it.

[Report a bug](../../issues/new?template=bug_report.md) · [Request a feature](../../issues/new?template=feature_request.md) · [Discussions](../../discussions)

</div>
