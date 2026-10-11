<div align="center">

# ☁️ CloudLap

### Turn your laptop into a personal cloud. Connect Claude AI from anywhere.

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org)
[![MCP](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io)

**Free • No API Keys • Works from Phone • Your Data Stays on Your Machine**

[Quick Start](#-quick-start) • [How It Works](#-how-it-works) • [Features](#-features) • [Security](#-security)

</div>

---

## 🤯 What is CloudLap?

CloudLap turns your laptop into a **free, personal cloud** that Claude AI can access from **anywhere** — your phone, a friend's laptop, a tablet, anything with a browser.

It's like having your own **Cowork / Replit / GitHub Codespaces** — but running on YOUR machine, for FREE.

```
Your Phone (anywhere)          Your Laptop (at home)
┌─────────────────────┐       ┌──────────────────────┐
│  Claude AI           │──────│  CloudLap Server      │
│  "Create a React app"│ MCP  │  → runs npm create    │
│                      │──────│  → creates files      │
│  "Fix the bug"       │      │  → reads error logs   │
│                      │      │  → fixes code         │
└─────────────────────┘       └──────────────────────┘
     Uses Claude's               Your laptop does
     built-in connector           all the work
```

## ✨ Features

| Feature | Description |
|---|---|
| 🔧 **Run Commands** | Execute any shell command on your laptop from Claude |
| 📄 **Read Files** | Read any file on your machine |
| ✏️ **Write Files** | Create and edit files remotely |
| 📂 **Browse Files** | List and explore your directories |
| 🔍 **Search Files** | Find files by name pattern across your machine |
| 💻 **System Info** | Check CPU, RAM, disk, OS info |
| 🧠 **Persistent Memory** | Context survives across sessions and accounts |
| 📋 **Save/Load Context** | Switch Claude accounts without losing progress |
| 🔐 **Security Blocklist** | Dangerous commands are automatically blocked |
| 🌐 **Permanent URL** | Same URL every time — set up Claude connector once |
| 📱 **Works Everywhere** | Phone, tablet, friend's laptop — any browser |
| 💰 **100% Free** | No API keys, no subscriptions, no cloud costs |

## 🚀 Quick Start

### Prerequisites
- **Windows 10/11** (macOS/Linux coming soon)
- **Python 3.10+** ([Download](https://python.org/downloads) — check "Add to PATH")
- **Free ngrok account** ([Sign up](https://dashboard.ngrok.com/signup) — 30 seconds)

### Step 1: Clone & Install
```bash
git clone https://github.com/YOUR_USERNAME/cloudlap.git
cd cloudlap
pip install -r requirements.txt
```

### Step 2: Set up ngrok (one time)
```bash
# Install ngrok
winget install ngrok.ngrok

# Add your auth token (from https://dashboard.ngrok.com/get-started/your-authtoken)
ngrok config add-authtoken YOUR_TOKEN_HERE

# Get your free static domain (from https://dashboard.ngrok.com/domains)
# You'll get something like: your-name.ngrok-free.dev
```

### Step 3: Configure
```bash
# Copy the example config
copy config.example.json config.json

# Edit config.json and set your ngrok domain:
```
```json
{
  "ngrok_domain": "your-name.ngrok-free.dev"
}
```

### Step 4: Start
```bash
# Option A: GUI App
python launcher.pyw
# Click START

# Option B: Command line
python server.py
# In another terminal:
ngrok http --url=your-name.ngrok-free.dev 8787
```

### Step 5: Connect Claude
1. Open [Claude](https://claude.ai) or the Claude mobile app
2. Go to **Settings** → **Connectors** → **Add Custom Connector**
3. Name: `CloudLap`
4. URL: `https://your-name.ngrok-free.dev/mcp`
5. Save!

### Step 6: Chat! 🎉
```
You: "List the files on my Desktop"
Claude: *uses your laptop's tools* → shows your actual files

You: "Create a React portfolio site"
Claude: *runs commands on your laptop* → builds the entire project
```

## 🔄 Persistent Memory (Switch Accounts Without Losing Context)

CloudLap saves context to your laptop, so you can switch Claude accounts and keep your progress:

```
Account 1: "Save our context"
→ Claude saves everything to your laptop

*switch to Account 2*

Account 2: "Load my context"
→ Claude reads saved context → continues exactly where you left off
```

Tools: `save_context`, `load_context`, `append_memory`, `list_projects`

## 🛡️ Security (Built to Fix OpenClaw's Mistakes)

CloudLap was designed with security lessons from OpenClaw's 500+ vulnerabilities:

| Vulnerability | OpenClaw | CloudLap |
|---|---|---|
| No audit trail | ❌ No logging | ✅ **Every tool call logged** to `audit_log.jsonl` |
| No rate limiting | ❌ Unlimited abuse | ✅ **30 calls/minute** rate limiter |
| Access to sensitive files | ❌ `.ssh`, `.env` exposed | ✅ **Sensitive paths blocked** automatically |
| No directory sandbox | ❌ Full filesystem access | ✅ **Configurable `allowed_directories`** |
| Dangerous commands | ❌ `rm -rf /` allowed | ✅ **12+ pattern blocklist** |
| Runaway processes | ❌ No timeouts | ✅ **120-second timeout** |
| Insecure defaults | ❌ Open by default | ✅ **Secure by default** |
| No encryption | ❌ HTTP possible | ✅ **HTTPS only** (via ngrok) |

Additional security:
- ✅ **No open ports** — no firewall/router changes needed
- ✅ **Your data stays on YOUR machine** — no cloud storage
- ✅ **No plugins/skills system** — no attack surface for malicious extensions

> ⚠️ **Important:** Your ngrok URL is accessible to anyone who has it. Keep it private.

## 📁 Project Structure

```
cloudlap/
├── server.py           # MCP server (10 tools for Claude)
├── launcher.pyw        # GUI app (click START to launch)
├── config.json         # Settings (port, ngrok domain, timeouts)
├── setup.bat           # One-click Windows installer
├── start.bat           # CLI launcher (server + tunnel)
├── requirements.txt    # Python dependencies
├── LICENSE             # MIT License
└── memory/             # Persistent context storage (created at runtime)
```

## 🆚 CloudLap vs Paid Alternatives

| Feature | Cowork ($20/mo) | Replit ($25/mo) | Codespaces ($$$) | **CloudLap (Free)** |
|---|---|---|---|---|
| AI + Execution | ✅ | ✅ | ✅ | ✅ |
| Access from Phone | ❌ | ✅ | ✅ | ✅ |
| Uses YOUR Machine | ✅ | ❌ | ❌ | ✅ |
| Persistent Memory | ❌ | ❌ | ❌ | ✅ |
| Cross-account Context | ❌ | ❌ | ❌ | ✅ |
| Cost | $240/yr | $300/yr | $$$ | **$0** |

## 🤝 Contributing

Contributions welcome! Ideas:
- [ ] macOS / Linux support
- [ ] Docker sandboxing for safer command execution
- [ ] Web dashboard UI
- [ ] OAuth authentication
- [ ] Multi-machine management
- [ ] File upload/download from phone
- [ ] Push notifications for command approval

## 📄 License

MIT — do whatever you want with it.

---

<div align="center">

**If CloudLap saved you money, give it a ⭐**

[Report Bug](../../issues) • [Request Feature](../../issues) • [Discussions](../../discussions)

</div>
