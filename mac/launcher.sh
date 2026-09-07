#!/bin/bash
# Finder runs this when the app is double-clicked. The uploader is a
# conversation — it asks where your Zwift folder is and for your setup code —
# so it needs a window to talk in, and Terminal is that window.
#
# It is told to RUN A COMMAND, not to open a file. `open -a Terminal <file>`
# asks LaunchServices to launch that file, and LaunchServices assesses it on
# its own: a console binary inside a bundle is "valid but does not seem to be
# an app", which is refused with an "Apple could not verify" dialog naming the
# inner program. Handing Terminal a command line instead runs it the way any
# shell does, under the app's own approval.
here="$(cd "$(dirname "$0")" && pwd)"
bin="$here/../Resources/velogenius-uploader/velogenius-uploader"

# Belt and braces: if this copy still carries a quarantine flag (dragged out
# of the disk image, say) and lives somewhere writable, clear it. Harmless
# when there is nothing to clear, and silent when the location is read-only.
xattr -dr com.apple.quarantine "$here/.." 2>/dev/null || true

# Escape for AppleScript's string literal, then for the shell Terminal runs.
esc_bin=${bin//\\/\\\\}
esc_bin=${esc_bin//\"/\\\"}
osascript \
  -e 'tell application "Terminal"' \
  -e "  do script \"clear; '$esc_bin'; exit\"" \
  -e '  activate' \
  -e 'end tell' >/dev/null
