# App Brief: "Dictation 2" (working name)

A complete description of the app as it exists today, written so that someone who has never seen it can help **rebrand it**: choose a name, a visual identity, colors, typography, icons and a style for the interface.

Everything below describes the current, working version. Where something is unfinished or untested, it says so.

---

## 1. The app in one paragraph

Dictation 2 is a **private, offline voice-to-text app for the Mac**. You hold one key, speak, let go, and your words are typed into whatever app you're using: email, Slack, Notes, a browser, anything with a text box. It also includes a **meeting notetaker** that records calls (your voice and the other people's), writes a live transcript, and saves it as a note next to your own typed notes. All speech recognition happens **on the Mac itself**, with no internet connection, no account and no cloud. Nothing you say leaves the computer.

**One-line pitch (draft):** *Speak anywhere on your Mac. Private, instant, and offline.*

---

## 2. Who it's for

- People who write a lot: emails, messages, documents, prompts for AI tools.
- People in many meetings who want notes without paying for a cloud notetaker or sending recordings to a server.
- Bilingual users: it handles **English and Arabic** (and 90+ other languages the speech model knows).
- Privacy-conscious users and companies: recordings and transcripts stay on the device.

**Main competitors and inspiration:** Wispr Flow (dictation), Granola, Otter and Fireflies (meeting notes), and the dictation built into macOS. The key difference: **this app is fully offline**, with no subscription, no login and no data upload.

---

## 3. Where it works

| | |
|---|---|
| **Platform** | macOS only (desktop app) |
| **Hardware** | Macs with Apple silicon (M1 or newer) |
| **macOS version** | macOS 13 Ventura or newer. Some meeting features work best on macOS 14+ |
| **Works in** | Any app with a text field: Mail, Slack, Teams, WhatsApp, Notes, Word, Google Docs, ChatGPT/Claude in the browser, code editors… |
| **Meetings** | Zoom, Google Meet (in any browser), Microsoft Teams, FaceTime, Webex, Slack huddles, Discord, or anything that uses the microphone |
| **Internet** | Not needed. The speech model is built into the app (~460 MB) |
| **Install** | A standard Mac disk image (`.dmg`): drag the app to Applications |
| **Size** | About 500 MB, mostly the built-in speech model |

**Where the app lives on screen:**
1. **Menu bar icon** (top-right of the screen): always present, shows status.
2. **Floating recording bar** ("the pill"): a small capsule at the bottom-centre of the screen that appears while you speak.
3. **Main window**: history, notes, dictionary, snippets, settings.
4. **Notepad window**: a smaller side window for live meeting notes.
5. **Pop-up cards** ("toasts"): small cards in the top-right corner for reminders and alerts.

By default it's a **menu-bar app** (no Dock icon). Users can turn on a Dock icon in Settings.

---

## 4. Core feature: push-to-talk dictation

**How it works for the user:**
1. Click into any text box in any app.
2. **Hold the Right Option key (⌥)** and speak.
3. A small black capsule appears at the bottom of the screen with **live sound bars** that move with your voice.
4. **Let go of the key.** The capsule shimmers briefly while it thinks, then your text is typed where your cursor is.

**Smart clean-up that happens automatically:**
- **Filler words removed:** "um", "uh", "hmm", "you know", "I mean", "sort of"… are dropped.
- **Self-correction ("backtrack"):** say *"scratch that"*, *"never mind"* or *"delete that"* to erase the last sentence. Say *"no wait"* or *"I meant"* to replace the last few words.
  Example: *"Meet at 3pm, no wait, 4pm"* becomes **"Meet at 4pm."**
- **Capitalisation and punctuation** tidied.
- **Personal dictionary:** names and terms spelled your way (e.g. company names, Arabic names in English letters).
- **Snippets (text shortcuts):** say a short trigger and longer text is typed instead. Example: say *"my email"* and get `amira@example.com`; say *"sign off"* and get "Best regards,".
- **Safety net:** every dictation is saved to history *before* it's typed, so if it didn't land in a text box you can copy it again.

**Speed:** with a fixed language, about 2.3–2.5 seconds for a 5-second sentence on a slow test Mac, and expected to be faster on a normal Mac. "Auto-detect" takes about twice as long.

**Languages:** a setting chooses **Auto-detect**, **English** or **Arabic**. Picking one language is about twice as fast as auto-detect.

**Optional behaviours while dictating (Settings):**
- Play a soft start and stop sound.
- Mute all Mac audio while you speak.
- Pause Music or Spotify while you speak, then resume (experimental).

---

## 5. Meeting notetaker

**Start it** with the keyboard shortcut **⌥ M** (changeable), the menu bar, or the **Notetaker** button on the Notes page.

**What it does:**
- Records **your microphone and the computer's sound** (so the other people on the call are captured too).
- Splits the recording at natural pauses and transcribes in the background, so the **transcript appears live**, a few seconds behind, with timestamps (`0:00`, `0:14`…).
- Filters out text the speech engine invents during silence, and collapses repeated phrases.
- Saves everything into a **meeting note** with a title, your own typed notes, the transcript and the duration.

**Meeting detection and automation:**
- **Calendar heads-up:** reads the Mac's Calendar (works with iCloud, Google and Exchange accounts added to macOS) and shows a card before a meeting starts. Timing options: Off, at start, 15 sec, 1 min, 2 min or 5 min before. The card has a **"Take notes"** button.
- **Next meeting in the menu bar:** shows the meeting name and a countdown next to the icon, e.g. `Design review · in 12m`.
- **Automatic call detection:** when another app starts using the microphone (a call begins), a card asks *"Call detected in Zoom. Take notes?"*
- **Stops automatically when the call ends** (optional).
- **Maximum recording length:** 30 min to 4 hours, with a warning card 2 minutes before it stops.
- **Recording indicator:** while recording, the menu bar shows a red dot and a timer (`● 12:34`).

**Notepad window:**
- A compact side window showing the meeting in progress: editable title, a red recording bar with timer and **Stop** button, a free-text area for your own notes, and the live transcript underneath.
- Can open automatically when the notetaker starts.
- **Split screen:** can place the meeting app on the left half of the screen and the Notepad on the right half.

**Privacy options:**
- **Hide from screen sharing:** the Notepad, the recording bar and the pop-up cards can be made invisible in screenshots and screen shares.
- The interface reminds the user to **always ask for consent before transcribing** a meeting.

**Status:** recording your own voice works. Recording the other participants depends on a macOS permission ("Screen & System Audio Recording") and was just fixed; it still needs confirming on a real call.

---

## 6. Notes

- A **Notes page** with a list of notes on the left and an editor on the right.
- Two kinds of note: **plain notes** (type or dictate into them) and **meeting notes** (with a transcript).
- The list shows the title, date and time, a **MEETING** tag, and a short preview. A red dot marks a note that is recording right now.
- Each note can be:
  - **edited** (title and body save automatically as you type);
  - **dictated into** (hold Right ⌥ while the note is open);
  - **copied as Markdown** (formatted text with title, notes and timestamped transcript);
  - **exported** as a `.md` file;
  - **opened in the Notepad window**;
  - **deleted** (click once and the button turns red: "Click again to delete").

---

## 7. Every screen, in detail

### 7.1 Main window (1000 × 660 px, resizable, minimum 760 × 520)

Two-column layout: a **sidebar** on the left (≈212 px) and a **content area** on the right.

**Sidebar (top to bottom):**
- App logo (small rounded square with a dot) and app name.
- Navigation: **Dictation** (home), **Notes**, **Clipboard**, **Dictionary**, **Snippets**, a divider, then **Settings**. Each item has a thin line icon. Notes shows a small pulsing red dot while a meeting is recording.
- A hint card at the bottom: "Hold **Right ⌥** to talk. Press **⌥ M** to take meeting notes."

**Pages:**

| Page | What's on it |
|---|---|
| **Dictation (home)** | Greeting "Welcome back" and "Everything you've dictated, on this Mac only." Three stat cards: **total words**, **words per minute**, **day streak**. A history list grouped by day (TODAY, YESTERDAY, then dates): time on the left, the dictated text, and a Copy button on hover. "Clear history" button (needs two clicks) |
| **Notes** | Note list + editor (see section 6). Buttons: **New note**, **Notetaker** (turns into a red **Stop** while recording) |
| **Clipboard** | The last 100 dictations as cards; click one to copy it ("Copied ✓" turns green) |
| **Dictionary** | A text field to add words, shown as removable chips |
| **Snippets** | Two fields (trigger → expansion) and a list of snippets with Remove buttons |
| **Settings** | Three tabs: **System**, **Notetaker**, **Experimental**; see section 8 |

### 7.2 Notepad window (440 × 680 px)
Single column, no sidebar: title, meta line ("Today, 10:04 · Meeting"), red recording bar with timer and Stop, notes area, transcript, and buttons (Copy as Markdown, Export…, Open in Dictation). With nothing recording it shows "No meeting in progress" and a **Start Notetaker** button.

### 7.3 Recording pill (112 × 34 px)
A small black capsule at the bottom-centre of the screen, above the Dock. Eleven white vertical bars:
- **Recording:** bars dance with your voice (taller in the middle, smooth rise and fall).
- **Thinking:** a soft shimmer travels across the bars.
- **Idle** (only if "show the bar at all times" is on): dimmed, flat bars.

It floats above everything, including full-screen apps, and can't be clicked.

### 7.4 Menu bar icon and menu
- **Icon states:** an outlined circle (ready), a busy circle (loading or thinking), a **red dot** (recording), and "!" (error). The black icons adapt automatically to light and dark menu bars.
- **Text next to the icon:** the next meeting with a countdown, or the recording timer.
- **Menu items:** Open Dictation · New Note · Start/Stop Notetaker (⌥ M) · Copy Last Dictation · next meeting ("Design review · 3:00 pm — Take notes") · status line ("Ready — hold ⌥ Right to dictate") · Quit. A warning item appears if Accessibility permission is missing.

### 7.5 Pop-up cards (340 px wide)
Dark rounded cards in the top-right corner with a bold title, a short message, and one or two buttons. Used for:
- "Design review starts in 15s" → [Take notes] [Dismiss]
- "Call detected in Zoom" → [Take notes] [Not now]
- "Notetaker stops in 2 minutes"
- "Meeting notes saved · Weekly sync · 12:34" → [Open] [Dismiss]
- Error messages, e.g. when a permission is missing.

### 7.6 Sounds
Uses built-in macOS sounds: **Tink** (start), **Pop** (stop), **Glass** (pop-up cards). These are a branding opportunity: custom sounds could become part of the identity.

---

## 8. All settings (with current defaults)

**System tab**
| Setting | Default |
|---|---|
| Language (Auto-detect / English / Arabic) | Auto-detect |
| Launch app at login | Off |
| Show the recording bar at all times | Off |
| Show app in Dock | Off |
| Dictation and notification sounds | On |
| Mute all audio while dictating | Off |

**Notetaker tab**
| Setting | Default |
|---|---|
| Notify before scheduled meetings start | 15 sec |
| Show your next meeting in the menu bar | On |
| Automatically detect any call | On |
| Maximum recording length | 2 hours |
| Stop Notetaker when a call ends | On |
| Keyboard shortcut (change by pressing new keys) | ⌥ M |
| Don't show Notepad and bar in screen capture | Off |
| Open Notepad when starting Notetaker | On |
| Split the screen when joining | Off |
| Show live transcript | On |
| Transcribe other participants (system audio) | On |

**Experimental tab**
| Setting | Default |
|---|---|
| Pause music while dictating (Music, Spotify) | Off |

---

## 9. Current visual design (what exists today)

The look was just changed to a **light-blue sidebar and frosted-glass content**, with clean, minimal typography. Treat it as a starting point, not a final brand.

**Style:** macOS-native, calm, minimal. Real frosted glass: the desktop shows through the window, blurred. Rounded cards, thin lines, plenty of white space. Full **light and dark mode**.

**Colours (light mode)**
| Role | Value |
|---|---|
| Sidebar | Light blue `rgba(214, 232, 250, 0.86)` |
| Sidebar text | Deep navy `#102640` |
| Content area | White glass `rgba(255, 255, 255, 0.58)` over a blurred desktop |
| Cards | White `rgba(255, 255, 255, 0.62)` with a soft white rim |
| Main text | Near-black `#0F1720` |
| Secondary text | Slate grey `#67717F` |
| Accent (buttons, switches) | Blue `#2E6FE0` |
| Recording / danger | Red `#D93B30` |

**Colours (dark mode):** navy-glass sidebar `rgba(28, 44, 66, 0.86)`, dark glass content, text `#EEF2F7`, accent `#5B9BF8`, red `#F0605A`.

**Typography:** the Mac system font (SF Pro) only.
| Use | Size / weight |
|---|---|
| Page titles | 24 px, semibold, slightly tight letter-spacing |
| Note titles | 24 px, semibold |
| Section titles | 13 px, semibold |
| Body text | 13.5–14.5 px, regular |
| Small labels (TODAY, TRANSCRIPT) | 11 px, semibold, uppercase, letter-spaced |
| Stats | 26 px, semibold, tabular numbers |

**Shapes:** card corners 12 px, buttons 8 px, switches fully rounded, recording pill fully rounded.

**Icons:** thin-line icons (1.7 px stroke) in the sidebar. The app icon is a black rounded square with a white dot (a simple "record" symbol).

**Voice and tone of the interface:** short, plain, friendly English. "Hold Right ⌥ to talk." "Nothing yet. Hold Right ⌥ and start talking." "Everything you've dictated, on this Mac only."

---

## 10. Where the brand appears (everything a rebrand would touch)

| Surface | Today | Notes for the designer |
|---|---|---|
| **App name** | "Dictation 2" (working name, so it can sit beside an older "Dictation") | Shown in Finder, Launchpad, Dock, window, menu, macOS permission prompts |
| **App icon** | Black rounded square, white dot | Needs a full macOS icon set (16 px up to 1024 px), and must read well at tiny sizes |
| **Menu bar icons** | 3 states: idle, busy, recording | 18 × 18 pt, single-colour "template" images (macOS tints them for light/dark). Recording state may use colour |
| **Recording pill** | Black capsule, white bars | The most-seen element: appears every time you speak. A strong brand moment (shape, colour, animation) |
| **Sidebar logo + wordmark** | Rounded square + name | Top-left of the main window |
| **Colours and type** | See section 9 | All defined in one place in the code, so easy to change |
| **Pop-up cards** | Dark cards, system buttons | Top-right corner |
| **Sounds** | Built-in Mac sounds | Could be custom branded sounds |
| **Disk image (installer)** | Plain window: app + Applications shortcut | Can have a branded background image and window layout |
| **Interface copy** | Plain English | Brand voice can be applied to every label and message |
| **Permission prompts** | "Dictation uses your microphone…" | Text shown by macOS when asking for mic, calendar and so on |
| **Data folder** | `~/Library/Application Support/Dictation 2` | Changes with the name |
| **Bundle ID** | `com.amira.dictation2` | Technical identifier; changes with the brand |

---

## 11. Technical facts that affect design choices

- The **main window and Notepad are web pages** (HTML/CSS) inside a native Mac window, so **any web-style design is possible**: custom fonts, gradients, animation, illustrations.
- The **recording pill, pop-up cards and menu bar** are **native Mac elements**, drawn in code. They can be restyled, but simple shapes and colours work best.
- **Real frosted glass** comes from macOS itself. Other materials (solid, tinted, darker glass) are a one-line change.
- **Light and dark mode** are both required: every colour needs a dark version.
- **Custom fonts** can be bundled. The system font is used today for a native feel.
- **Right-to-left text:** Arabic transcripts already display correctly. Consider Arabic in the brand (a bilingual name? Arabic typography?).
- **No server, no login, no account:** there is no sign-up flow or web dashboard to design, unless the brand adds one.
- **Distribution:** today it's an ad-hoc signed DMG (macOS warns on first open). A paid Apple Developer account ($99/year) makes it install cleanly; needed before sharing widely.

---

## 12. Known limitations (honest status)

- **Mac only**, and Apple-silicon only.
- Meeting capture of **other participants** was just fixed and needs testing on a real call.
- Call detection identifies the calling app best on **macOS 14+**.
- **Auto-detect language** is about twice as slow as choosing a language.
- The meeting transcript doesn't say **who** is speaking (no speaker labels yet).
- **No sharing** of notes via links: notes are local; you can copy or export them.
- No iPhone or Windows version.

---

## 13. Ideas the brand could grow into (not built yet)

- Speaker labels ("You" / "Them") in meeting transcripts.
- AI summaries and action items after a meeting (could stay on-device).
- Faster engine using the Mac's graphics chip.
- Custom vocabulary packs per company or industry.
- Team or enterprise version (shared dictionary and snippets, managed install).
- Onboarding tutorial on first launch.

---

## 14. Questions to answer when branding

1. **Name:** should it say what it does (Speak, Dictate, Voice…), or be abstract? Bilingual (English/Arabic)? Must be available as a Mac app name and domain.
2. **Positioning:** "private dictation", "offline meeting notes", or both equally?
3. **Personality:** calm and minimal (like Apple / Things), bold and playful (like Arc), or premium and serious (like Linear)?
4. **Colour:** keep light blue and glass, or a signature colour that also works for the recording pill and menu bar icon?
5. **The recording pill:** what should the moment of speaking look and feel like? This is the signature interaction.
6. **Icon:** an abstract mark, a sound wave, a microphone, a letter, or something tied to the name?
7. **Sounds:** keep the Mac's sounds or create branded start/stop sounds?
8. **Audience:** individuals, teams, or companies (affects tone, pricing story and website)?
9. **Arabic:** is Arabic-language support a headline feature of the brand?
