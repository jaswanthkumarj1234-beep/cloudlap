<div align="center">

# ☁️ CloudLap

### Your laptop is your cloud. Control it from anywhere with Claude AI.

[![CI](https://github.com/jaswanthkumarj1234-beep/cloudlap/actions/workflows/ci.yml/badge.svg)](https://github.com/jaswanthkumarj1234-beep/cloudlap/actions)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![MCP](https://img.shields.io/badge/MCP-Compatible-8B5CF6?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCI+PHRleHQgeT0iMTgiIGZvbnQtc2l6ZT0iMTgiPjwvdGV4dD48L3N2Zz4=)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-22C55E)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-26_passed-22C55E)](tests/)
[![Security](https://img.shields.io/badge/Security-Hardened-22C55E)](SECURITY.md)

**Free** · **No API keys** · **Works from phone** · **Your data stays on your machine**

[Quick Start](#-quick-start) · [Features](#-features) · [Security](#-security-built-to-fix-openclaws-mistakes) · [Contributing](#-contributing)

---

</div>

## 🤯 What is CloudLap?

CloudLap turns your laptop into a **free, personal cloud** that Claude AI can control from **anywhere** — your phone, a friend's laptop, a coffee shop tablet. It uses [Model Context Protocol (MCP)](https://modelcontextprotocol.io) to give Claude direct, secure access to your machine.

**Think of it as your own free Cowork / Replit / Codespaces — running on YOUR hardware.**

```
  Your Phone (anywhere)              Your Laptop (at home)
 ┌────────────────────────┐        ┌────────────────────────┐
 │  Claude AI              │───────│  CloudLap Server        │
 │                         │  MCP  │                         │
 │  "Create a React app"   │◄──────│  → runs npm create      │
 │  "Fix the bug on L42"   │       │  → reads error logs     │
 │  "Deploy to Vercel"     │       │  → pushes to git        │
 └────────────────────────┘        └────────────────────────┘
      You use Claude's                 Your laptop does
      built-in connector               all the heavy lifting
```

## ✨ Features

| | Feature | Description |
|---|---|---|
| 🔧 | **Run Commands** | Execute any shell command — build, test, deploy |
| 📄 | **Read Files** | Read any file on your machine (up to 100KB) |
| ✏️ | **Write Files** | Create and edit files, auto-create directories |
| 📂 | **Browse Files** | List and explore directories with sizes and dates |
| 🔍 | **Search Files** | Find files by pattern across your entire machine |
| 💻 | **System Info** | Live CPU, RAM, disk, OS, battery stats |
| 🧠 | **Persistent Memory** | Context survives across sessions and accounts |
| 📋 | **Save/Load Context** | Switch Claude accounts without losing progress |
| 🛡️ | **Security Hardened** | Audit log, rate limiting, directory sandbox, command blocklist |
| 🌐 | **Permanent URL** | Same URL forever — configure Claude connector once |
| 📱 | **Works Everywhere** | Phone, tablet, any browser, any device |
| 💰 | **100% Free** | No API keys, no subscriptions, zero cloud costs |

## 🚀 Quick Start

### Prerequisites

- **Windows 10/11** (macOS/Linux support planned — [help wanted!](../../issues))
- **Python 3.10+** — [Download](https://python.org/downloads) (check "Add to PATH")
- **Free ngrok account** — [Sign up](https://dashboard.ngrok.com/signup) (30 seconds)

### 1. Clone & Install

```bash
git clone https://github.com/jaswanthkumarj1234-beep/cloudlap.git
cd cloudlap
pip install -r requirements.txt
```

### 2. Set Up ngrok (one time)

```bash
# Install ngrok
winget install ngrok.ngrok

# Add your auth token (from https://dashboard.ngrok.com/get-started/your-authtoken)
ngrok config add-authtoken YOUR_TOKEN

# Claim your free static domain at https://dashboard.ngrok.com/domains
# You'll get something like: cool-name-here.ngrok-free.dev
```

### 3. Configure

```bash
copy config.example.json config.json
```

Edit `config.json` — set your ngrok domain:

```json
{
  "ngrok_domain": "cool-name-here.ngrok-free.dev"
}
```

### 4. Launch

```bash
# GUI mode (recommended)
python launcher.pyw

# CLI mode
python server.py
# In another terminal:
ngrok http --url=cool-name-here.ngrok-free.dev 127.0.0.1:8787
```

### 5. Connect Claude

1. Open [claude.ai](https://claude.ai) (or Claude mobile app)
2. **Settings** → **Connectors** → **Add Custom Connector**
3. Name: `CloudLap`
4. URL: `https://cool-name-here.ngrok-free.dev/mcp`
5. Done! Start chatting. 🎉

```
You: "Create a Python web scraper and save it to my Desktop"
Claude: *creates the file on your actual Desktop*

You: "Run it and show me the results"
Claude: *executes the script on your laptop, returns output*
```

## 🔄 Persistent Memory

CloudLap's killer feature: **context that survives across sessions and accounts.**

```
Account 1 (free tier limit hit):
  You: "Save our context"
  Claude: → saves everything to your laptop's memory/

  *switch to Account 2*

Account 2 (new session):
  Claude: → auto-reads instructions → finds saved context
  Claude: "I see we were building a portfolio site. Continuing..."
```

The server sends instructions to Claude on every connection telling it to check for saved context. It happens automatically.

**Tools:** `save_context` · `load_context` · `append_memory` · `list_projects`

## 🛡️ Security (Built to Fix OpenClaw's Mistakes)

CloudLap was designed with security lessons from [OpenClaw's 500+ vulnerabilities](https://nvd.nist.gov/):

| Risk | OpenClaw | CloudLap |
|---|---|---|
| No audit trail | ❌ Zero logging | ✅ **Every call logged** to `audit_log.jsonl` |
| No rate limiting | ❌ Unlimited abuse | ✅ **30 calls/min** rate limiter |
| Sensitive file access | ❌ `.ssh`, `.env` exposed | ✅ **Auto-blocked** always |
| No directory sandbox | ❌ Full filesystem | ✅ **Configurable** `allowed_directories` |
| Dangerous commands | ❌ `rm -rf /` allowed | ✅ **12+ pattern** blocklist |
| Runaway processes | ❌ No timeouts | ✅ **120s timeout** kill switch |
| Insecure defaults | ❌ Open by default | ✅ **Secure by default** |
| Malicious plugins | ❌ "Claw Chain" attack | ✅ **No plugin system** = no attack surface |

> ⚠️ **Your ngrok URL gives full access to your machine.** Keep it private. See [SECURITY.md](SECURITY.md) for hardening tips.

## 🆚 CloudLap vs Paid Alternatives

| Feature | Cowork (\$20/mo) | Replit (\$25/mo) | Codespaces (\$\$\$) | **CloudLap** |
|---|:---:|:---:|:---:|:---:|
| AI + Code Execution | ✅ | ✅ | ✅ | ✅ |
| Access from Phone | ❌ | ✅ | ✅ | ✅ |
| Uses YOUR Machine | ✅ | ❌ | ❌ | ✅ |
| Persistent Memory | ❌ | ❌ | ❌ | ✅ |
| Cross-account Context | ❌ | ❌ | ❌ | ✅ |
| Audit Log | ❌ | ❌ | ✅ | ✅ |
| **Cost** | \$240/yr | \$300/yr | \$\$\$ | **\$0** |

## 📁 Project Structure

```
cloudlap/
├── server.py              # MCP server — 10 tools for Claude
├── launcher.pyw           # GUI app — one-click START/STOP
├── config.example.json    # Config template (copy to config.json)
├── setup.bat              # One-click Windows installer
├── start.bat              # CLI launcher (server + tunnel)
├── requirements.txt       # Python dependencies
├── tests/
│   └── test_server.py     # 26 unit tests
├── .github/
│   ├── workflows/ci.yml   # CI pipeline (Python 3.10/3.11/3.12)
│   └── ISSUE_TEMPLATE/    # Bug report & feature request templates
├── CONTRIBUTING.md         # How to contribute
├── SECURITY.md             # Security policy & hardening
├── CHANGELOG.md            # Version history
├── LICENSE                 # MIT
└── memory/                 # Created at runtime — persistent context storage
```

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**High-impact areas:**
- [ ] 🍎 macOS / Linux support
- [ ] 🐳 Docker containerized deployment
- [ ] 🌐 Web-based dashboard UI
- [ ] 🔐 OAuth / token authentication
- [ ] 📊 Built-in analytics dashboard
- [ ] 📱 Push notifications for command approval
- [ ] 🖥️ Multi-machine management

## 📄 License

[MIT](LICENSE) — use it however you want.

---

<div align="center">

**If CloudLap helped you, give it a ⭐**

It takes 1 second and helps others discover it.

[Report Bug](../../issues/new?template=bug_report.md) · [Request Feature](../../issues/new?template=feature_request.md) · [Security](SECURITY.md)

</div>
