"""dmgbuild settings: a laid-out disk image, built without Finder.

The obvious way to place icons in a DMG is AppleScript at the Finder, which
needs a logged-in desktop and automation consent — neither of which a build
machine has. dmgbuild writes the .DS_Store itself, so the window looks the
same everywhere and the build stays headless.
"""

import os

application = os.environ["APP_PATH"]
appname = os.path.basename(application)

format = "UDZO"
files = [application]
symlinks = {"Applications": "/Applications"}
background = os.environ["DMG_BACKGROUND"]

icon_size = 128
text_size = 13
label_pos = "bottom"
# Matches the background art, which is drawn to the same coordinates.
icon_locations = {appname: (165, 178), "Applications": (495, 178)}
window_rect = ((240, 160), (660, 360))

default_view = "icon-view"
show_status_bar = False
show_tab_view = False
show_toolbar = False
show_pathbar = False
show_sidebar = False
show_icon_preview = False
arrange_by = None
