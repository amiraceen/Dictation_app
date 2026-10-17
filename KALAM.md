# Kalam (كلام)

**Write less, speak more.**

Kalam is a private voice-to-text app for the Mac. Hold one key, speak, let go, and your words are typed wherever your cursor is: email, WhatsApp Web, Slack, Notes, Google Docs, a browser, or any app with a text box.

It understands **Arabic and English**, including Gulf and Omani Arabic, Modern Standard Arabic, Egyptian and Levantine. All speech recognition happens **on the Mac itself**. There's no account, no subscription and no cloud, and nothing you say leaves the computer.

*Powered by Amira Hamood.*

---

## What it does

| You do | Kalam does |
|---|---|
| Hold **Right Option ⌥** and talk | Records your voice and shows a small bar with live sound levels at the bottom of the screen |
| Let go of the key | Turns your speech into text and types it into the app you're using |
| Say "scratch that" or "no wait" | Fixes the sentence the way you meant it. *"Meet at 3, no wait, 4"* becomes *"Meet at 4."* |
| Say a shortcut such as "my email" | Types the full text you saved for it |
| Pause, say "um" or "uh" | Leaves out the filler words and adds punctuation |

Everything you say is also saved in Kalam, so nothing is lost if it didn't land in a text box.

## How people use it

- **Writing messages faster:** reply to emails, WhatsApp and Slack by talking instead of typing.
- **Writing in Arabic without an Arabic keyboard:** speak naturally in your dialect and get Arabic text with Western digits (1, 2, 3).
- **Switching languages:** speak Arabic in one message and English in the next. Kalam works out which language you used each time.
- **Drafting longer text:** captions, briefs, notes, ideas and to-do lists, spoken as fast as you think.
- **Notes:** keep quick notes inside the app, and dictate straight into them.
- **Brand and client names:** teach Kalam how to spell the names you use often, like *Ceen Marketing*.
- **Accessibility:** less typing for people with hand or wrist strain, or anyone who thinks better out loud.

## What it provides

### The main window

A clean window with five round icons in the top bar. Hover over any icon to preview what's inside.

| Page | What's there |
|---|---|
| **Home (Transcribe)** | Your history grouped by day, plus total words, words per minute and your daily streak. Copy any past text with one click. |
| **Notes** | Write notes, dictate into them, copy a note as text, export it as a file, or open it in its own small window. |
| **Clipboard** | Your last 100 transcriptions. Click one to copy it again. |
| **Your words** | Names, brands and terms Kalam should spell your way. |
| **Shortcuts** | Say a short trigger, and Kalam types the longer text you saved for it (your email, address, sign-off). |
| **Settings** | Language, speech model, app language, sounds and start-up options. |

### Clearing history

You decide what to keep:
- clear a **single day** with the trash button next to it;
- or use **Clear history** to remove **today**, the **last 7 days**, the **last 30 days** or **everything**.

Every clear asks you to click twice, so nothing is deleted by accident.

### Speech models

| Model | Best for | Size | Speed (5-second clip) |
|---|---|---|---|
| **Fast** (built in) | English and quick notes; works right after install | Included | About 3 to 5 seconds on the processor |
| **Accurate** (optional download) | Arabic dialects and mixed Arabic and English | 1.6 GB, downloaded once from Settings | About 0.3 seconds on the Mac's graphics chip |
| **Large** (optional download) | The full Whisper large-v3; about as accurate as Accurate, worth trying on your own voice | 3.1 GB | About 2.5 times slower than Accurate |
| **Arabic dialects** (optional download) | Accurate retrained by the community on Arabic dialects; may suit everyday speech better, weaker on formal Arabic | 3.2 GB download, stored as 1.6 GB | Same as Accurate |

The Accurate model is also told which dialect words to expect (Gulf, Omani, Egyptian and Levantine), so casual speech comes out as you said it, not as formal Arabic.

### Arabic and English interface

The whole app (window, menus and messages) can be shown in **English or Arabic** from Settings → App language. Arabic mode switches the layout to right to left and uses Arabic banners. The Arabic wording was reviewed for natural, everyday Gulf phrasing, not word-for-word translation.

### Settings at a glance

- **Speaking language:** Arabic or English (auto), Arabic only, or English only. Picking one language makes text appear faster.
- **Speech model:** Fast, Accurate, Large or Arabic dialects.
- **App language:** English or العربية.
- **Launch at login**, **show the Kalam bar at all times**, **show the app in the Dock**.
- **Sounds** when recording starts and stops.
- **Mute all audio** or **pause Music and Spotify** while you talk.

## Privacy

- Speech is turned into text **on your Mac**; recordings are never uploaded.
- History, notes, your words, shortcuts and settings are stored only on your Mac, in `~/Library/Application Support/Kalam`.
- The only time Kalam goes online is when you choose to download the Accurate model.
- To erase everything: quit Kalam and delete that folder.

## What you need

- A Mac with **Apple silicon** (M1 or newer). A MacBook Air works well.
- macOS 13 Ventura or newer.
- Permissions, asked the first time:
  - **Microphone**, to hear you;
  - **Accessibility**, for the Right Option key and typing into other apps;
  - **Automation**, only if you turn on pausing Music or Spotify.

## Getting started

1. Open **Kalam.dmg** and drag **Kalam** into **Applications**.
2. Open Kalam. If macOS says it can't verify the app, go to **System Settings → Privacy & Security** and click **Open Anyway**.
3. Allow the **Microphone**, then switch Kalam on under **Privacy & Security → Accessibility**.
4. Wait for the Kalam icon in the menu bar, then hold **Right Option ⌥** and talk.
5. Optional, for best Arabic: open **Settings** and choose the **Accurate** speech model.

## How it's built (for the curious)

- **Speech recognition:** OpenAI's Whisper models running locally, *small* on the processor (faster-whisper) and *large-v3-turbo* on the graphics chip (Apple MLX).
- **Arabic support:**
  - automatic Arabic or English detection that doesn't mistake short dialect phrases for Hebrew or Persian;
  - Arabic punctuation and Western digits;
  - Arabic versions of "scratch that" and filler-word removal.
- **App:** Python with native macOS windows (AppKit and WebKit). The interface is a single web page inside the app, with every phrase in one English and Arabic wording file.
- **Quality checks:** every build is tested automatically on a Mac. The tests cover the app's logic, every button in the window (in English and Arabic), clicks in the real app window, and a test transcription, before the download is produced.

---

**Kalam** · Write less, speak more. · Powered by Amira Hamood
