#!/bin/bash
# Finder runs this when the app is double-clicked. The uploader is a
# conversation — it asks where your Zwift folder is and for your setup code —
# so it needs a window to talk in. Hand it to Terminal rather than run it
# blind with nowhere to print.
#
# The uploader itself lives under Contents/Resources: Apple's bundle rules
# allow only executables in Contents/MacOS, and a PyInstaller build carries
# a zip of the standard library and other plain files beside its binary.
here="$(cd "$(dirname "$0")" && pwd)"
exec open -a Terminal "$here/../Resources/velogenius-uploader/velogenius-uploader"
