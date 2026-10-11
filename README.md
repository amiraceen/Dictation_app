# Dictation App 2026

Private, offline push-to-talk dictation for macOS. Hold **Right Option ⌥**, speak, release, and the text appears in whatever app you're typing in. Speech recognition runs on your Mac with [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (Whisper *small*), so nothing is sent to the internet.

## Features

- **Push-to-talk anywhere:** hold Right Option to record, release to paste into the active app.
- **Recording pill:** a floating black capsule with live sound bars while you talk.
- **Backtrack:** say "scratch that", "never mind" or "no wait" to correct yourself. *"Meet at 3pm, no wait, 4pm"* becomes *"Meet at 4pm."*
- **Clipboard backup:** every dictation is saved before pasting, so you can copy it again from the Clipboard tab.
- **Main window:** history with total words, words per minute and day streak, plus Dictionary and Snippets pages.
- **Dictionary:** names and terms the model should spell your way.
- **Snippets:** say a short trigger to type longer text.
- **Filler removal:** drops "um", "uh" and similar words.
- **Languages:** English and Arabic, plus any other language Whisper detects.

## Install (ready-made app)

Requires a Mac with Apple silicon (M1 or newer).

1. Download **Dictation.zip** from the [Releases](../../releases) page, unzip it, and drag **Dictation** into **Applications**.
2. Open it. macOS will say it can't verify the app, because it is self-signed, not notarized by Apple. Click **Done**, then go to **System Settings → Privacy & Security** and click **Open Anyway**.
3. Click **Allow** when it asks for the microphone.
4. Go to **System Settings → Privacy & Security → Accessibility** and switch **Dictation** on. If it isn't listed, add it with **+**.
5. Wait for the filled circle in the menu bar, then hold **Right Option** and talk.

Your history, dictionary and snippets are stored in `~/Library/Application Support/Dictation`.

## Run from source

```bash
bash setup.sh      # creates venv and installs requirements
bash run.sh        # first run downloads the Whisper small model (~460 MB)
```

Grant your terminal app **Microphone** and **Accessibility** permission.

## Build the app

```bash
venv/bin/pyinstaller --noconfirm Dictation.spec
```

The build bundles the Whisper model from your Hugging Face cache, so run it from source once first. `build_pkg.sh` builds, signs and installs to `/Applications`. It signs with a local code-signing certificate named **Dictation Local Signing**; create your own, or replace that step with `codesign --force --deep -s - dist/Dictation.app` (ad-hoc signing). With ad-hoc signing you have to re-grant Accessibility after every rebuild.

## Project layout

| File | Purpose |
|---|---|
| `dictation.py` | Core: recording, transcription, backtrack, snippets, history store, menu bar |
| `ui.py` | Native recording pill (NSPanel) and main window (WKWebView bridge) |
| `web/index.html` | Main window interface |
| `menubar/`, `AppIcon.icns`, `icon/` | Menu-bar and app icons |
| `Dictation.spec` | PyInstaller build definition |
| `main.m`, `main.swift`, `build_app.sh` | Earlier native prototype using Apple Speech (separate app) |
