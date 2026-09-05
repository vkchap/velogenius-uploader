# VeloGenius Uploader

Sends your Zwift rides to [VeloGenius](https://velogenius.ai) so your training
history is complete — including rides that never reach Strava, and with the
full detail Zwift records that other services strip out.

It reads `.fit` ride files from your Zwift folder and nothing else.

## Setting it up (about a minute)

**1. Get your setup code.** Sign in at [velogenius.ai](https://velogenius.ai),
go to **Settings**, and find the *Zwift uploader* section.

**2. Start the uploader.**

- **Windows:** download
  [VeloGenius-Uploader.exe](https://github.com/vkchap/velogenius-uploader/releases/latest/download/VeloGenius-Uploader.exe)
  and double-click it. The first time, Windows shows *"Windows protected your
  PC"* because the file is new to it: click **More info**, then **Run anyway**.
  Nothing else to install.
- **Mac:** copy the one-line command shown in Settings and paste it into
  Terminal (Applications › Utilities). It fetches this script into your home
  folder and starts it. Next time, run `python3 ~/velogenius_uploader.py`.

**3. Answer two questions.** It finds your Zwift folder and shows you how many
rides are in it; you confirm, then paste your setup code. That's the whole
setup — it remembers from then on.

The first run uploads everything it finds. After that it only sends new rides.

## While it runs

Leave the window open and new rides upload on their own, a minute or so after
you finish riding. Close it whenever you like — nothing is lost, and it catches
up the next time you start it.

To upload once and quit, run it with `--once`.

## Sending a folder of files from another device

Tymewear or Garmin exports, for instance. This is a one-off and does not
change your Zwift folder setting:

    VeloGenius-Uploader.exe --folder C:\Users\you\Downloads\tymewear
    python3 ~/velogenius_uploader.py --folder ~/Downloads/tymewear

## If macOS blocks reading your Documents folder

The first time, macOS may ask whether Terminal can read your Documents folder.
Click **OK** — that's the folder Zwift saves rides in. If you clicked
*Don't Allow*, the uploader will tell you so rather than silently doing
nothing. To change it: **System Settings › Privacy & Security › Files and
Folders**, and switch on **Documents** for Terminal.

## Questions you might have

**What does it send?** Only `.fit` ride files from the folder you confirmed.
Nothing else on your computer is read.

**Can I stop it?** Close the window. To disconnect entirely, revoke the setup
code in VeloGenius Settings — the uploader stops working immediately.

**Does it upload the same ride twice?** No. It remembers what it has sent, and
VeloGenius refuses duplicates as well, so re-running it is always safe.

**Where does my setup code live?** In `~/.velogenius/uploader.json`, readable
only by you. Delete that file to start over.

## Building

The Windows executable is built by GitHub Actions from `velogenius_uploader.py`
on every push to `main` and published as the rolling `latest` release. It
bundles its own Python, so nothing needs installing.
