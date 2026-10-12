# Known Limitations

An honest list of what CloudLap does not yet handle well, with suggested mitigations.
Contributions that address any of these are welcome.

## 1. Availability
| Limitation | Impact | Mitigation |
|---|---|---|
| The host computer is a single point of failure (sleep, lid close, battery, power cut) | Every tool fails with an execution error until the machine is back | Set sleep/hibernate to "never" while in use; keep the machine plugged in; set the lid action to "do nothing" |
| Nothing starts the server or tunnel at login | After a reboot or Windows update the lab stays offline | Add a Startup-folder shortcut or service for the server and tunnel; consider auto sign-in |
| No watchdog | If the server or tunnel crashes it is not restarted | Run a small supervisor loop that relaunches either process |
| The tunnel is a hard dependency (ngrok/cloudflared) | Free tiers can rotate URLs, add interstitial pages, or rate limit | Use a reserved/static domain or a named Cloudflare tunnel |
| Low-RAM hosts | Heavy commands can fail or stall the whole machine | Run one heavy job at a time; monitor with `get_system_info` |

## 2. Context and memory
| Limitation | Impact | Mitigation |
|---|---|---|
| Context is only saved when the model calls `save_context` | There is no end-of-chat hook, so an abrupt end loses recent work | Save at milestones; keep the activity log on |
| A saved context is a summary, not the conversation | Reasoning and exact wording are lost | Keep a decision log (see `docs/CONTEXT_SYSTEM.md`) |
| `save_context` overwrites the project snapshot | History of earlier snapshots is lost | Keep an append-only log next to the snapshot |
| No "active project" pointer | A new chat does not know which project to load; the `default` project is often empty | Save a `default` context that points to the active project |
| A new chat only loads context if told to (or if it follows the server instructions) | Behavior depends on the model. The first tool result of a session now carries a reminder, but a chat that never calls a tool never sees it | Say "Load my context for default" at the start, or add a standing instruction in your account settings |
| No drift check between saved state and the disk | Notes can claim files exist that were moved or edited | Compare listed files against the disk on load |
| No locking between concurrent sessions or accounts | Two chats can overwrite each other's snapshot | Use per-project names; avoid saving the same project from two chats at once |
| The auto activity log keeps only state-changing actions, 120 characters each, last 200 lines | User requests, decisions, outcomes and errors are not recorded | Add an explicit decision log |
| Memory is stored as plain text on disk | May contain secrets or personal data | Never save tokens or passwords; keep `memory/` out of version control (already in `.gitignore`) |

## 3. Security
| Limitation | Impact | Mitigation |
|---|---|---|
| The command filter is a blocklist | Blocklists can be bypassed (for example a blocked command's equivalent in another shell) | Prefer the directory sandbox and an allowlist for sensitive deployments |
| Remote command execution is reachable over a public URL | Anyone with the URL and credentials has the same access as the owner | Keep the token secret; rotate it; restrict the tunnel with IP or OAuth rules where the provider supports it |
| The audit log is local and not tamper-evident | The same tools that run commands could edit the log | Ship the log to a separate location or append-only store |
| Sensitive-path blocking is name based | Unusual locations for secrets are not covered | Add custom patterns to the config |
| No account separation | Every account connected to the same server sees the same memory | Treat one server as one trust domain |

## 4. Functionality
| Limitation | Impact | Mitigation |
|---|---|---|
| `read_file` returns text up to 100 KB | Images, binaries and large files cannot be viewed | Convert or chunk files before reading |
| `run_command` output is truncated and commands time out (about 120 seconds) | Long jobs and installers are killed along with their child processes | Start long jobs detached and poll a log file |
| No screen, camera or audio tools | The assistant cannot see the machine | Add a screenshot tool, or use a remote desktop app as a backup |
| Windows-oriented assumptions | `cmd` quirks (`&` chaining, `%VAR%` expansion, `>` redirection) cause surprising results | Use scripts or PowerShell for anything non-trivial |
| Tests cover the security helpers and config only | Activity log, tunnel handling and context tools are untested | Add tests for those areas |
