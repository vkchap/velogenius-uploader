#!/bin/bash
# Finder runs this when the app is double-clicked. The uploader is a
# conversation — it asks where your Zwift folder is and for your setup code —
# so it needs a window to talk in. Hand it to Terminal rather than run it
# blind with nowhere to print.
here="$(cd "$(dirname "$0")" && pwd)"
exec open -a Terminal "$here/velogenius-uploader/velogenius-uploader"
