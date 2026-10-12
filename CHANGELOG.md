# Changelog

All notable changes to CloudLap are documented here.

## [Unreleased]

### Added
- Two-factor unlock: tools stay locked until `unlock` is called with a code from an authenticator app (`totp.py`, `totp_setup.py`)
- `SETUP.md`: step-by-step setup guide including the authenticator step
- `setup_wizard.py`: one guided setup (requirements, authenticator QR with code check, ngrok, auto-start); `setup.bat` now runs it
- Server logs a loud warning at startup when no authenticator lock is set up

### Features
- `watchdog.ps1`: keeps the server and ngrok tunnel running, single instance, rolling `watchdog.log`; start it hidden at login. It also asks Windows not to sleep while it runs; set `"keep_display_on": true` in `config.json` to keep the screen on as well
- Automatic activity log: state-changing `write_file` and `run_command` calls are recorded in `memory/activity_log.md` (last 200 lines) and appended to `load_context` output
- Session nudge: the first tool call of a new session (or after 30 idle minutes) is followed by a reminder listing saved projects and telling the model to call `load_context`

### Documentation
- Added `docs/CONTEXT_SYSTEM.md` (resuming work across chats and accounts)
- Added `docs/KNOWN_LIMITATIONS.md` (availability, context, security and functional limits, with mitigations)
- Documented that the MCP endpoint has no authentication of its own and that the server listens on `0.0.0.0` (see `docs/KNOWN_LIMITATIONS.md`)

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
