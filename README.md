# Dictation App 2026

Private, offline push-to-talk dictation for macOS. Hold **Right Option ⌥**, speak, release, and the text appears in whatever app you're typing in. Speech recognition runs on your Mac with [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (Whisper *small*), so nothing is sent to the internet.

## Features

- **Push-to-talk anywhere:** hold Right Option to record, release to paste into the active app.
- **Recording pill:** a floating black capsule with live sound bars while you talk.
- **Backtrack:** say "scratch that", "never mind" or "no wait" to correct yourself. *"Meet at 3pm, no wait, 4pm"* becomes *"Meet at 4pm."*
- **Clipboard backup:** every dictation is saved before pasting, so you can copy it again from the Clipboard tab.
- **Main window:** history with total words, words per minute and day streak, plus Your words and Shortcuts pages. Sections sit in a top bar of colourful circle icons; hover one to preview what's inside.
- **Your words:** names and terms the model should spell your way.
- **Shortcuts:** say a short trigger to type longer text.
- **Filler removal:** drops "um", "uh" and similar words.
- **Languages:** English and Arabic, plus any other language Whisper detects.
- **Notes:** write notes in the Notes page, or hold Right Option while a note is open to dictate into it. Copy any note as Markdown or export it to a `.md` file.
- **System settings:** launch at login, show the bar at all times, show the app in the Dock, sounds, mute all audio while dictating, and (experimental) pause Music or Spotify while dictating.

## Install (ready-made app)

Requires a Mac with Apple silicon (M1 or newer).

1. Download **Dictation.zip** from the [Releases](../../releases) page, unzip it, and drag **Dictation** into **Applications**.
2. Open it. macOS will say it can't verify the app, because it is self-signed, not notarized by Apple. Click **Done**, then go to **System Settings → Privacy & Security** and click **Open Anyway**.
3. Click **Allow** when it asks for the microphone.
4. Go to **System Settings → Privacy & Security → Accessibility** and switch **Dictation** on. If it isn't listed, add it with **+**.
5. Wait for the filled circle in the menu bar, then hold **Right Option** and talk.

This build installs as **Kalam**, a separate app from the original **Dictation** and from **Dictation 2**: it has its own app ID, permissions and data folder (`~/Library/Application Support/Kalam`). On first launch it copies everything from Dictation 2's data folder (history, words, shortcuts, notes, settings, voice test), or from the original Dictation if Dictation 2 was never installed; it never changes the older apps' files. Because it's a new app, macOS asks for Microphone and Accessibility permission again. Quit the other apps before using Kalam, since they all listen for Right Option.

Your history, dictionary, snippets, notes and settings are stored in `~/Library/Application Support/Kalam`.

### Permissions

macOS asks for each of these the first time the feature needs it. You can change them later in **System Settings → Privacy & Security**:

| Permission | Used for |
|---|---|
| **Microphone** | Hearing you while you hold Right Option. |
| **Accessibility** | The Right Option hotkey and typing the text where your cursor is. |
| **Automation** | Pausing Music or Spotify and muting audio while you dictate. |

## Run from source

```bash
bash setup.sh      # creates venv and installs requirements
bash run.sh        # first run downloads the Whisper small model (~460 MB)
```

Grant your terminal app **Microphone** and **Accessibility** permission.

## Build the app

**Disk image (DMG):** every push to GitHub builds `Kalam.dmg` on a GitHub-hosted Mac (see `.github/workflows/build-macos.yml`). Open the repo's **Actions** tab, pick the latest **Build macOS app** run and download **Kalam-dmg** under Artifacts. Pushing a tag such as `v1.1` also publishes the DMG on the **Releases** page. To build it on your own Mac instead, run `bash build_dmg.sh` (output: `dist/Kalam.dmg`).

The DMG is ad-hoc signed unless you add a certificate. To ship a build that opens without the **Open Anyway** step, add these repository secrets: `MACOS_CERT_P12` (base64 Developer ID certificate), `MACOS_CERT_PASSWORD` and `MACOS_SIGN_IDENTITY`. For notarization, also add `NOTARY_APPLE_ID`, `NOTARY_TEAM_ID` and `NOTARY_PASSWORD` (an app-specific password).

**Manual build:**

```bash
venv/bin/pyinstaller --noconfirm Dictation.spec
```

The build bundles the Whisper model from your Hugging Face cache, so run it from source once first. `build_pkg.sh` builds, signs and installs to `/Applications`. It signs with a local code-signing certificate named **Dictation Local Signing**; create your own, or replace that step with `codesign --force --deep -s - dist/Dictation.app` (ad-hoc signing). With ad-hoc signing you have to re-grant Accessibility after every rebuild.

## Project layout

| File | Purpose |
|---|---|
| `dictation.py` | Core: recording, transcription, backtrack, snippets, history store, menu bar |
| `notes.py` | Notes storage (one JSON file per note) and Markdown export |
| `settings.py` | Settings with defaults and validation (`settings.json`) |
| `system.py` | Launch-at-login item and media-pause scripts |
| `macos.py` | macOS calls: launch at login, Dock icon, sounds, mute and media pause |
| `tests/` | Unit tests and an app wiring test with macOS stubbed (`python3 -m unittest discover -s tests`) |
| `ui.py` | Native recording pill, pop-up cards (NSPanel), main window and Notepad (WKWebView bridge) |
| `web/index.html` | Main window interface |
| `menubar/`, `AppIcon.icns`, `icon/` | Menu-bar and app icons |
| `Dictation.spec` | PyInstaller build definition |
| `main.m`, `main.swift`, `build_app.sh` | Earlier native prototype using Apple Speech (separate app) |

## Brand

**Kalam** (كلام, "speech"). The look comes from the brand artwork in `docs/brand/`: an open sky blue, a warm sunrise beam, sun yellow and deep night green at the edges, with film grain over everything. The window has frosted glass over a soft gradient in those colours, colourful circle icons in the top bar, and pill-shaped buttons. While you talk, the recording pill is clear glass with orange-to-blue bars.

- Logo: `docs/brand/logo-full.svg` (wordmark) and `logo-mark.svg` (the "k"). The window's top bar uses the wordmark; the menu bar uses the mark (black when idle, faded while working, orange while recording).
- Header: the Transcribe page shows one of the four "Write less, speak more." banners (`web/img/header-*.webp`, from `docs/brand/`, with the export's light edge trimmed), picked each time the window opens.
- Colours: sky `#5DA1D0`, deep blue `#1C5E9B`, sunrise orange `#FD6D39`, sun `#FFE284`, night `#10222B`.
- Font: [Readex Pro](https://github.com/ThomasJockin/readexpro) (SIL Open Font License, bundled in `web/fonts/`), which covers Latin and Arabic.
- App icon: `python3 tools/make_icon.py` fits `docs/brand/app-icon-source.jpg` to the macOS icon shape and writes `AppIcon.icns` (preview: `docs/kalam-icon.png`).

## Testing

- `python3 -m unittest discover -s tests`: app logic, every button's action run through the app, Arabic clean-up, the speech engines (also run on every build).
- `NODE_PATH=$(npm root -g) node tests/ui_check.js`: clicks every button, toggle, menu and form in the window (Chromium + Playwright) and checks each one does its job.
