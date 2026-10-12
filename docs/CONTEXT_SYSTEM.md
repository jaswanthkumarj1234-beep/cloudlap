# Context System: resuming work across chats and accounts

CloudLap stores context on the host machine, not inside any chat or account.
Any account that connects to the same server can load the same saved context.

## What is saved
| Layer | Where | Written by | Purpose |
|---|---|---|---|
| Project snapshot | `memory/context_<project>.md` | `save_context` | Task, summary, files changed, next steps |
| Auto activity log | `memory/activity_log.md` | The server, automatically | Last 200 state-changing actions (file writes and selected commands) |
| Notes | memory notes | `append_memory` | Preferences and decisions |

`load_context` returns the snapshot plus the recent activity log.

## Starting a new chat or switching accounts
1. Connect the account to the same CloudLap server.
2. Say: "Load my context for default" (or name the project).
3. Keep a `default` context that points to the active project, so a new chat is never empty.

## Session nudge
The server's startup instructions list saved projects, but that list is fixed when the server starts.
To cover the gap, the first result of each new session (the first tool call, or any call after 30 idle
minutes) is followed by a one-line reminder with the current list of saved projects and a prompt to call
`load_context`. It is skipped when no context has been saved, and for `load_context` and `save_context`.
The tools' inputs are unchanged.

## Recommended practice (optional, user-maintained)
Keep an append-only decision log per project next to your work, one line per event:

    YYYY-MM-DD HH:MM | TYPE | detail

TYPE can be USER_REQUEST, DECISION, ACTION, FILE_CHANGE, COMMAND, RESULT, ERROR or NEXT.
Rewrite a short "resume brief" at the end of each session, and update the `default`
context so it names the active project. Never store passwords or tokens in any log.

## What this does not guarantee
- It is not a transcript. Only what the assistant chose to save or what the server logged is available.
- Saving is not automatic at the end of a chat. See `docs/KNOWN_LIMITATIONS.md`.
- Two chats saving the same project at once can overwrite each other.
