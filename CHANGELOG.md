# Changelog

All notable changes to CloudLap are documented here.

## [Unreleased]

### Features
- Automatic activity log: state-changing `write_file` and `run_command` calls are recorded in `memory/activity_log.md` (last 200 lines) and appended to `load_context` output

### Documentation
- Added `docs/CONTEXT_SYSTEM.md` (resuming work across chats and accounts)
- Added `docs/KNOWN_LIMITATIONS.md` (availability, context, security and functional limits, with mitigations)

## [1.1.0] - 2026-10-12

### 🛡️ Security
- Added **audit logging** — every tool call logged to `audit_log.jsonl` with timestamp, args, and status
- Added **rate limiting** — 30 calls/minute to prevent abuse
- Added **directory sandbox** — configurable `allowed_directories` in config
- Added **sensitive path blocking** — `.ssh`, `.env`, `.aws`, credentials always blocked
- Security comparison with OpenClaw's vulnerabilities in README

### 🧠 Features
- **Auto-context instructions** — Claude automatically loads saved context on new sessions
- **26 unit tests** covering security blocklist, sandbox, rate limiter, audit log, config
- **GitHub Actions CI** — automated testing on Python 3.10/3.11/3.12

### 🐛 Bug Fixes
- Fixed subprocess pipe buffer deadlock causing server freeze under heavy use
- Fixed IPv6 `[::1]` connection refused by targeting explicit `127.0.0.1:8787`
- Auto-cleanup of orphaned processes on port 8787 before launch
- Added WinGet ngrok path to launcher search locations

### 📦 Infrastructure
- Config template (`config.example.json`) — personal config gitignored
- Updated `setup.bat` and `start.bat` for ngrok (replaced cloudflared)
- Professional project structure: CONTRIBUTING, SECURITY, CHANGELOG, issue templates

## [1.0.0] - 2026-10-11

### 🚀 Initial Release
- 10 MCP tools: `run_command`, `read_file`, `write_file`, `list_directory`, `search_files`, `get_system_info`, `save_context`, `load_context`, `append_memory`, `list_projects`
- GUI launcher (CloudLap.exe) with dark theme
- Permanent URL via ngrok static domain
- Persistent memory system for cross-session/cross-account context
- Command security blocklist (12+ patterns)
- 120-second command timeout
- HTTPS encryption via ngrok tunnel
