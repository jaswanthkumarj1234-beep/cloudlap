# Security Policy

## Supported Versions

| Version | Status |
|---------|--------|
| 1.x     | Supported |

## Important

CloudLap gives Claude AI direct access to your computer. It can run commands, read and write files, and access system information. This is by design, but it means:

- Keep your ngrok URL private. Anyone with the URL has access.
- Do not run CloudLap on production servers.
- Review the command blocklist in `server.py` and customize it for your needs.

## Built-in Protections

- **Command blocklist** — 12+ regex patterns blocking destructive commands
- **Directory sandbox** — configurable `allowed_directories` in config
- **Sensitive path blocking** — `.ssh`, `.env`, `.aws`, credentials always denied
- **Rate limiting** — 30 calls/minute
- **Audit log** — every tool call recorded to `audit_log.jsonl`
- **Timeout** — commands killed after 120 seconds

## Reporting a Vulnerability

If you discover a security issue:

1. Do **not** open a public issue.
2. Use GitHub's [private vulnerability reporting](../../security/advisories/new).
3. Or contact the maintainer directly.

Response time: within 48 hours.

## Hardening

Restrict access to only the directories you need:

```json
{
  "allowed_directories": ["~/projects"],
  "timeout_seconds": 60
}
```

Consider using [ngrok IP restrictions](https://ngrok.com/docs/http/ip-restrictions/) for additional protection.
