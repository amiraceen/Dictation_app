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
- **Notes:** write notes in the Notes page, or hold Right Option while a note is open to dictate into it. Copy any note as Markdown or export it to a `.md` file.
- **Notetaker:** press **⌥ M** (changeable in Settings) to record a meeting. It transcribes as you go, so the transcript fills in every few seconds, and it saves everything to a meeting note. The recording also runs on your Mac.
  - **Meeting detection:** get a heads-up before calendar meetings (Off, at start, 15 sec, 1, 2 or 5 min), see your next meeting with a countdown in the menu bar, and get asked to take notes when another app starts using the mic for a call.
  - **Stops on its own:** at a maximum length you choose (30 min to 4 hours, with a warning 2 minutes before) and, optionally, when the call ends.
  - **Notepad:** a separate window for the live note. It can open when the Notetaker starts and can split the screen, with the meeting on the left and the Notepad on the right.
  - **Other participants:** records what your Mac plays as well as your mic, so the other people on the call are transcribed too.
  - **Privacy:** you can keep the Notepad, the bar and pop-ups out of screenshots and screen sharing. Always ask for consent before transcribing a meeting.
- **System settings:** launch at login, show the bar at all times, show the app in the Dock, sounds, mute all audio while dictating, and (experimental) pause Music or Spotify while dictating.

## Install (ready-made app)

Requires a Mac with Apple silicon (M1 or newer).

1. Download **Dictation.zip** from the [Releases](../../releases) page, unzip it, and drag **Dictation** into **Applications**.
2. Open it. macOS will say it can't verify the app, because it is self-signed, not notarized by Apple. Click **Done**, then go to **System Settings → Privacy & Security** and click **Open Anyway**.
3. Click **Allow** when it asks for the microphone.
4. Go to **System Settings → Privacy & Security → Accessibility** and switch **Dictation** on. If it isn't listed, add it with **+**.
5. Wait for the filled circle in the menu bar, then hold **Right Option** and talk.

This build installs as **Dictation 2**, a separate app from the original **Dictation**: it has its own app ID, permissions and data folder (`~/Library/Application Support/Dictation 2`). On first launch it copies your history, dictionary and snippets from the original app; it never changes the original's files. Quit one app before using the other, since both listen for Right Option.

Your history, dictionary, snippets, notes and settings are stored in `~/Library/Application Support/Dictation 2`.

### Permissions for the Notetaker

macOS asks for each of these the first time the feature needs it. You can change them later in **System Settings → Privacy & Security**:

| Permission | Used for |
|---|---|
| **Calendars** | Meeting heads-ups and the next meeting in the menu bar. Covers any account added to the Calendar app (iCloud, Google, Exchange). |
| **Screen & System Audio Recording** | Transcribing the other people on a call. Without it, only your mic is recorded. |
| **Accessibility** | The hotkeys (already needed for dictation) and splitting the screen. |
| **Automation** | Pausing Music or Spotify and muting audio while you dictate. |

Call detection needs macOS 14 or newer to tell which app is using the mic. On macOS 13 the app can still notice a call starting, but it can't notice the call ending while the Notetaker is recording.

## Run from source

```bash
bash setup.sh      # creates venv and installs requirements
bash run.sh        # first run downloads the Whisper small model (~460 MB)
```

Grant your terminal app **Microphone** and **Accessibility** permission.

## Build the app

**Disk image (DMG):** every push to GitHub builds `Dictation-2.dmg` on a GitHub-hosted Mac (see `.github/workflows/build-macos.yml`). Open the repo's **Actions** tab, pick the latest **Build macOS app** run and download **Dictation-2-dmg** under Artifacts. Pushing a tag such as `v1.1` also publishes the DMG on the **Releases** page. To build it on your own Mac instead, run `bash build_dmg.sh` (output: `dist/Dictation-2.dmg`).

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
| `notetaker.py` | Meeting recording: mixes mic and system audio, cuts it at pauses, transcribes in the background |
| `notes.py` | Notes storage (one JSON file per note) and Markdown export |
| `meetings.py` | Next meeting and countdown, heads-up timing, call start/end detection |
| `settings.py` | Settings with defaults and validation (`settings.json`) |
| `system.py` | Shortcut mapping, launch-at-login item, media-pause scripts, split-screen geometry |
| `macos.py` | macOS calls: CoreAudio mic detection, EventKit, ScreenCaptureKit, Accessibility, sounds |
| `tests/` | Unit tests and an app wiring test with macOS stubbed (`python3 -m unittest discover -s tests`) |
| `ui.py` | Native recording pill, pop-up cards (NSPanel), main window and Notepad (WKWebView bridge) |
| `web/index.html` | Main window interface |
| `menubar/`, `AppIcon.icns`, `icon/` | Menu-bar and app icons |
| `Dictation.spec` | PyInstaller build definition |
| `main.m`, `main.swift`, `build_app.sh` | Earlier native prototype using Apple Speech (separate app) |
