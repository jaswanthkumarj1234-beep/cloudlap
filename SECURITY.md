# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | ✅ Active |

## ⚠️ Important Security Note

CloudLap gives Claude AI **direct access to your computer** — it can run commands, read/write files, and access system information. This is by design, but it means:

- **Keep your ngrok URL private.** Anyone with your URL can control your machine.
- **Don't run CloudLap on production servers.** It's designed for personal development machines.
- **Review the command blocklist** in `server.py` and customize it for your needs.

## Built-in Security Features

- **Command Blocklist** — 12+ regex patterns blocking dangerous commands (`rm -rf`, `format`, `shutdown`, registry edits, encoded commands, etc.)
- **Directory Sandbox** — Configurable `allowed_directories` restricts file access
- **Sensitive Path Blocking** — `.ssh`, `.env`, `.aws`, credentials files are always blocked
- **Rate Limiting** — 30 calls/minute to prevent abuse
- **Audit Log** — Every tool call logged to `audit_log.jsonl`
- **Command Timeout** — 120-second kill switch for runaway processes

## Reporting a Vulnerability

If you discover a security vulnerability:

1. **DO NOT** open a public GitHub issue
2. Go to the [Security tab](../../security/advisories/new) → "Report a vulnerability"
3. Or email the maintainer directly

I'll respond within 48 hours and work on a fix.

## Hardening Recommendations

For extra security beyond defaults:

```json
{
  "allowed_directories": ["~/projects"],
  "timeout_seconds": 60
}
```

- Restrict `allowed_directories` to only the folders you need
- Lower the timeout for faster kill on bad commands
- Use ngrok's built-in auth features for URL protection
- Run CloudLap in a VM or container for full isolation
