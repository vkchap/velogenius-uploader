#!/usr/bin/env python3
"""VeloGenius Zwift Uploader — sends your Zwift rides to VeloGenius.

Written for cyclists, not developers: no installs, no config files to edit, no
command-line arguments needed. Double-click the launcher (or run this file) and
it walks you through setup once, then keeps watching for new rides.

Design rules, learned the hard way on a real machine:

  Never fail silently. macOS blocks access to Documents per-app, and Python's
  glob turns that refusal into an empty list — a tool that quietly uploads
  nothing is worse than one that crashes. Every skip says why.

  Never guess about the user's data. The folder is auto-detected from the
  places Zwift actually writes, including iCloud-synced Documents, and the
  count is shown before anything is sent.

  Never need a second tool. Standard library only, so any Mac or PC with
  Python can run it, and setup happens in this script rather than in a
  README the user has to follow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

APP_DIR = Path.home() / ".velogenius"
CONFIG_PATH = APP_DIR / "uploader.json"
LEDGER_PATH = APP_DIR / "uploaded.json"

DEFAULT_API = "https://api.velogenius.ai"
SETTINGS_URL = "https://velogenius.ai/app/settings"

# A file still being written must not be uploaded. Zwift names the live one
# explicitly, and anything touched in the last two minutes may still be open.
SETTLE_SECONDS = 120
POLL_SECONDS = 60
SKIP_NAMES = {"inprogressactivity.fit"}

# Everywhere Zwift is known to keep activities, in the order worth trying.
# iCloud's Documents sync relocates the real folder, which is why the plain
# path can exist as a symlink while the files live elsewhere.
CANDIDATE_DIRS = (
    "~/Documents/Zwift/Activities",
    "~/Library/Mobile Documents/com~apple~CloudDocs/Documents/Zwift/Activities",
    "~/OneDrive/Documents/Zwift/Activities",
    "~/Zwift/Activities",
)


# --- talking to the user ------------------------------------------------------


def say(msg: str = "") -> None:
    print(msg, flush=True)


def headline(msg: str) -> None:
    say()
    say(f"  {msg}")
    say("  " + "-" * len(msg))


def ask(prompt: str) -> str:
    """input() that fails kindly.

    Setup needs a person. Run without a terminal — from a scheduler, or with
    input piped in and exhausted — and input() raises EOFError and the user
    gets a traceback. Say what happened instead.
    """
    try:
        return input(prompt)
    except EOFError:
        say()
        say()
        say("  Setup needs someone to answer these questions, but there is no")
        say("  keyboard attached to this run.")
        say("  Run it from a Terminal window (or double-click the launcher)")
        say("  once, and it will remember the answers afterwards.")
        sys.exit(1)


def die(msg: str, *fixes: str) -> None:
    say()
    say(f"  Stopped: {msg}")
    for f in fixes:
        say(f"    - {f}")
    say()
    if sys.stdin.isatty():
        try:
            input("  Press Return to close. ")
        except EOFError:
            pass
    sys.exit(1)


# --- network ------------------------------------------------------------------


def ssl_context() -> ssl.SSLContext:
    """Verify properly even where Python shipped without a CA bundle.

    python.org's macOS builds install no certificates (that is what their
    "Install Certificates.command" is for), so the default context trusts
    nothing. The OS bundle is used as a fallback; verification is never off —
    this program carries a credential.
    """
    ctx = ssl.create_default_context()
    if not ctx.get_ca_certs() and os.path.exists("/etc/ssl/cert.pem"):
        ctx = ssl.create_default_context(cafile="/etc/ssl/cert.pem")
    return ctx


def api_get(cfg: dict, path: str) -> dict:
    req = urllib.request.Request(
        cfg["api_url"].rstrip("/") + path,
        headers={"Authorization": f"Bearer {cfg['token']}"},
    )
    with urllib.request.urlopen(req, timeout=30, context=ssl_context()) as resp:
        return json.loads(resp.read().decode())


def api_post_fit(cfg: dict, name: str, data: bytes) -> dict:
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        cfg["api_url"].rstrip("/") + "/uploads/fit",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {cfg['token']}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with urllib.request.urlopen(req, timeout=180, context=ssl_context()) as resp:
        return json.loads(resp.read().decode())


# --- finding the rides --------------------------------------------------------


def readable(path: Path) -> tuple[bool, str]:
    """(can we list it, why not). Distinguishes blocked from missing, always."""
    if not path.exists():
        return False, "not found"
    if not path.is_dir():
        return False, "not a folder"
    try:
        next(iter(os.scandir(path)), None)
    except PermissionError:
        return False, "blocked by macOS privacy settings"
    except OSError as e:
        return False, f"unreadable ({e.strerror})"
    return True, ""


def fit_files(path: Path) -> list[Path]:
    out = []
    try:
        for entry in os.scandir(path):
            if entry.is_file() and entry.name.lower().endswith(".fit"):
                if entry.name.lower() not in SKIP_NAMES:
                    out.append(Path(entry.path))
    except OSError:
        return []
    return sorted(out)


def find_zwift_folder() -> tuple[Path | None, list[str]]:
    """Auto-detect. Returns (folder, notes) — notes explain near-misses."""
    notes = []
    for cand in CANDIDATE_DIRS:
        p = Path(cand).expanduser()
        ok, why = readable(p)
        if ok:
            return p, notes
        if why != "not found":
            notes.append(f"{p} — {why}")
    return None, notes


# --- setup --------------------------------------------------------------------


def choose_folder(besides: Path | None = None) -> Path:
    """Which folder holds the rides. Offers the one we can find, then asks.

    `besides` is a folder already in use: there is no point offering the
    athlete the folder they are trying to move away from.
    """
    folder, notes = find_zwift_folder()
    if folder is not None and besides is not None and folder == besides:
        folder, notes = None, []

    say()
    if folder is not None:
        n = len(fit_files(folder))
        say(f"  Found your Zwift folder: {folder}")
        say(f"  It contains {n} ride file{'s' if n != 1 else ''}.")
        if ask("\n  Use this folder? [Y/n] ").strip().lower() in ("n", "no"):
            folder = None
    elif not notes:
        pass  # nothing to report: we simply did not look, or found the old one
    else:
        say("  I could not find your Zwift folder automatically.")
        for note in notes:
            say(f"    tried: {note}")

    while folder is None:
        say()
        say("  Where does Zwift save your rides? On a Mac this is usually")
        say("    ~/Documents/Zwift/Activities")
        say("  (In Finder: Go > Home > Documents > Zwift > Activities,")
        say("   then drag the folder into this window to paste its path.)")
        raw = ask("\n  Folder path: ").strip().strip("'\"")
        if not raw:
            die("no folder given", "Run this again when you know the folder.")
        cand = Path(raw).expanduser()
        ok, why = readable(cand)
        if not ok:
            say(f"  Cannot read that folder — {why}.")
            if "blocked" in why:
                say("  macOS is protecting it. Either:")
                say("    - allow this app when macOS asks, or")
                say("    - System Settings > Privacy & Security > Files and Folders")
            continue
        folder = cand
        n_found = len(fit_files(folder))
        say(f"  Using {folder} ({n_found} ride file{'s' if n_found != 1 else ''}).")
    return folder


def confirm_folder(cfg: dict) -> dict:
    """Say which folder is about to be watched, and offer to change it.

    Setup runs once and is then never seen again, so a folder chosen wrongly —
    or a folder that later moves — used to be unreachable from the app: the
    only way out was to find and delete the settings file. Asking here costs
    one keypress and makes it recoverable.

    Skipped when nothing can answer. A run with no keyboard (launched by a
    script, or piped) must start watching rather than sit on a question, and
    ask() would otherwise stop the whole thing.
    """
    watch = Path(cfg["watch_dir"])
    ok, why = readable(watch)
    say(f"  Watching: {watch}")
    if not ok:
        say(f"  Cannot read it — {why}.")
    elif n := len(fit_files(watch)):
        say(f"  {n} ride file{'s' if n != 1 else ''} in it.")
    else:
        # Worth saying plainly. An empty folder is the shape of a wrong
        # folder, and this is the moment it can still be corrected.
        say("  No ride files in it yet.")

    if not sys.stdin.isatty():
        return cfg

    prompt = "\n  Press Return to start, or C to use a different folder: "
    if ask(prompt).strip().lower() not in ("c", "change"):
        return cfg

    cfg = {**cfg, "watch_dir": str(choose_folder(besides=watch))}
    save_config(cfg)
    say(f"  Saved. From now on it watches {cfg['watch_dir']}.")
    return cfg


def save_config(cfg: dict) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=1))
    CONFIG_PATH.chmod(0o600)


def run_setup() -> dict:
    headline("VeloGenius Zwift Uploader — first-time setup")
    say()
    say("  This sends your Zwift ride files to VeloGenius so your training")
    say("  history stays complete. It only ever reads .fit files, and only")
    say("  from the folder you confirm below.")

    folder = choose_folder()

    say()
    say(f"  Now the setup code. Sign in at {SETTINGS_URL}")
    say("  and copy the code under 'Zwift uploader'.")
    cfg = {"api_url": DEFAULT_API, "watch_dir": str(folder)}
    while True:
        token = ask("\n  Paste your setup code: ").strip()
        if not token:
            die("no setup code given", f"Get one at {SETTINGS_URL}")
        cfg["token"] = token
        try:
            status = api_get(cfg, "/uploads/status")
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                say("  That code was refused. Copy the whole thing and try again.")
                continue
            if e.code == 404:
                die(
                    "this uploader is newer than the VeloGenius server",
                    "Wait for the next deploy, or download the uploader again.",
                )
            die(f"the server said {e.code}", "Try again in a few minutes.")
        except urllib.error.URLError as e:
            die(f"cannot reach VeloGenius ({e.reason})", "Check your internet connection.")
        say(f"  Connected — hello {status['athlete']}.")
        break

    save_config(cfg)
    say(f"  Saved to {CONFIG_PATH}")
    return cfg


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return run_setup()
    try:
        cfg = json.loads(CONFIG_PATH.read_text())
    except Exception:
        say("  Your settings file was unreadable; starting setup again.")
        return run_setup()
    if not all(cfg.get(k) for k in ("api_url", "token", "watch_dir")):
        return run_setup()
    return cfg


# --- the work -----------------------------------------------------------------


def load_ledger() -> dict:
    if LEDGER_PATH.exists():
        try:
            return json.loads(LEDGER_PATH.read_text())
        except Exception:
            pass
    return {}


def save_ledger(ledger: dict) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(ledger, indent=1))


def upload_new(cfg: dict, ledger: dict, *, verbose: bool) -> tuple[int, int]:
    """Returns (uploaded, skipped_recent)."""
    watch = Path(cfg["watch_dir"])
    ok, why = readable(watch)
    if not ok:
        say(f"  Cannot read {watch} — {why}.")
        if "blocked" in why:
            say("  macOS is blocking this app from your Documents folder.")
            say("  Fix: System Settings > Privacy & Security > Files and Folders,")
            say("  switch on Documents for Terminal (or whatever you launched this")
            say("  with), then run this again.")
        return 0, 0

    files = fit_files(watch)
    now = time.time()
    pending = []
    too_recent = 0
    for path in files:
        try:
            if now - path.stat().st_mtime < SETTLE_SECONDS:
                too_recent += 1
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
        if digest not in ledger:
            pending.append((path, digest))

    if not pending:
        if verbose:
            say(
                f"  Nothing new — all {len(files)} ride "
                f"file{'s' if len(files) != 1 else ''} already uploaded."
                if files
                else "  Nothing to send yet."
            )
        return 0, too_recent

    say(f"  Uploading {len(pending)} new ride file{'s' if len(pending) != 1 else ''}...")
    sent = 0
    for i, (path, digest) in enumerate(pending, start=1):
        try:
            out = api_post_fit(cfg, path.name, path.read_bytes())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                die(
                    "VeloGenius refused the setup code",
                    f"Get a fresh one at {SETTINGS_URL},",
                    f"then delete {CONFIG_PATH} and run this again.",
                )
            say(f"    [{i}/{len(pending)}] {path.name} — refused ({e.code}), skipping")
            continue
        except (urllib.error.URLError, TimeoutError) as e:
            say(f"    [{i}/{len(pending)}] {path.name} — no connection, will retry ({e})")
            break
        ledger[digest] = {"file": path.name, "id": out.get("id"), "at": int(now)}
        save_ledger(ledger)
        sent += 1
        say(f"    [{i}/{len(pending)}] {path.name}")
    return sent, too_recent


def main() -> int:
    ap = argparse.ArgumentParser(description="Send Zwift rides to VeloGenius.")
    ap.add_argument("--once", action="store_true", help="upload and exit (no watching)")
    ap.add_argument("--setup", action="store_true", help="redo setup")
    # A one-off folder of ride files from somewhere other than Zwift — a batch
    # of Tymewear or Garmin exports, say. Uses the saved setup code, sends
    # what is there, and exits; the Zwift folder setting is not touched.
    ap.add_argument("--folder", metavar="PATH", help="send the .fit files in PATH once, then exit")
    args = ap.parse_args()

    if args.setup and CONFIG_PATH.exists():
        CONFIG_PATH.unlink()
    cfg = load_config()

    if args.folder:
        ok, why = readable(Path(args.folder).expanduser())
        if not ok:
            die(f"cannot read {args.folder} — {why}", "Check the path and try again.")
        cfg = {**cfg, "watch_dir": str(Path(args.folder).expanduser())}
        args.once = True

    headline("VeloGenius Zwift Uploader")
    say()
    if args.folder:
        # An explicit one-off folder was named on the command line; there is
        # nothing to confirm and nothing to remember.
        say(f"  Watching: {cfg['watch_dir']}")
    else:
        cfg = confirm_folder(cfg)
    say()

    first = True
    try:
        while True:
            sent, recent = upload_new(cfg, load_ledger(), verbose=first)
            if first and sent:
                say()
                say(f"  Done — {sent} ride file{'s' if sent != 1 else ''} sent.")
            if recent and first:
                say(f"  ({recent} file{'s' if recent != 1 else ''} just finished; will send shortly.)")
            if args.once:
                say()
                say("  Finished. Your rides are on velogenius.ai.")
                return 0
            if first:
                say()
                say("  Leave this window open — new rides upload automatically.")
                say("  (Close it any time; nothing is lost, it catches up on the next run.)")
            first = False
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        say()
        say("  Stopped. Run this again whenever you like.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
