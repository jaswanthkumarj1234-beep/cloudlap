#!/usr/bin/env bash
# Removes the CloudLap services. Asks before deleting your authenticator secret and saved data.
set -uo pipefail
UID_NUM="$(id -u)"
AGENTS="$HOME/Library/LaunchAgents"
for n in server tunnel; do
  launchctl bootout "gui/$UID_NUM/com.cloudlap.$n" >/dev/null 2>&1 || true
  rm -f "$AGENTS/com.cloudlap.$n.plist"
done
echo "CloudLap services stopped and removed."
if [ -r /dev/tty ]; then
  read -r -p "Also delete ~/.cloudlap (secret, saved contexts, logs)? Type yes to delete: " a </dev/tty
  if [ "$a" = "yes" ]; then rm -rf "$HOME/.cloudlap"; echo "Deleted ~/.cloudlap."; else echo "Kept ~/.cloudlap."; fi
fi
echo "Remember to delete the CloudLap entry from your authenticator app and the connector from Claude."
