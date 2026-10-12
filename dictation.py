#!/usr/bin/env python3
"""
Dictation App — macOS
Hold RIGHT OPTION (⌥) to record, release to transcribe and type.
"""

import json
import os
import re
import subprocess
import threading
import time

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from pynput import keyboard

from notetaker import clean_transcript
from speed import DECODE, whisper_language

try:
    import rumps
    HAS_RUMPS = True
except ImportError:
    HAS_RUMPS = False

# ─── Paths ───────────────────────────────────────────────────────────────────

import sys

FROZEN = getattr(sys, "frozen", False)   # True inside the packaged .app
APP_NAME = "Dictation 2"     # separate app and data folder, so it can sit beside the original Dictation


def _copy_from_original(app_dir):
    """First launch: copy (never move) history, dictionary and snippets from the original app."""
    import shutil
    old = os.path.expanduser("~/Library/Application Support/Dictation")
    if os.path.isdir(app_dir) or not os.path.isdir(old):
        return
    os.makedirs(app_dir)
    for name in ("history.json", "dictionary.txt", "snippets.json"):
        try:
            shutil.copy2(os.path.join(old, name), os.path.join(app_dir, name))
        except OSError:
            pass


if FROZEN:
    # Bundle is read-only; user-editable files live in Application Support.
    APP_DIR = os.path.expanduser(f"~/Library/Application Support/{APP_NAME}")
    _copy_from_original(APP_DIR)
    os.makedirs(APP_DIR, exist_ok=True)
    MODEL_PATH = os.path.join(sys._MEIPASS, "model")
    RES_DIR = sys._MEIPASS
    # No terminal in the packaged app: send output to a log file.
    sys.stdout = sys.stderr = open(os.path.join(APP_DIR, "dictation.log"), "a", buffering=1)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    MODEL_PATH = None
    RES_DIR = APP_DIR
SNIPPETS_FILE = os.path.join(APP_DIR, "snippets.json")
DICT_FILE     = os.path.join(APP_DIR, "dictionary.txt")
HISTORY_FILE  = os.path.join(APP_DIR, "history.json")
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")
NOTES_DIR     = os.path.join(APP_DIR, "notes")
WEB_HTML      = os.path.join(RES_DIR, "web", "index.html")

# ─── Config ──────────────────────────────────────────────────────────────────

SAMPLE_RATE  = 16000
HOTKEY       = keyboard.Key.alt_r   # Hold RIGHT OPTION ⌥
MODEL_SIZE   = "small"              # small = much better accuracy than base
LANGUAGE     = None                 # None = auto-detect (supports 100+ languages)
MIN_DURATION = 0.3
COMPUTE_TYPE = "int8"
TYPING_DELAY = 0.03               # transcription already takes longer than the key release

ICON_IDLE         = "🎤"
ICON_LOADING      = "⏳"
ICON_RECORDING    = "🔴"
ICON_TRANSCRIBING = "⚙️"
ICON_ERROR        = "❌"

FILLER_WORDS = {
    "um", "uh", "umm", "uhh", "hmm", "mhm", "hm",
    "like", "basically", "literally", "actually",
    "you know", "i mean", "sort of", "kind of",
    "right", "okay so", "so yeah", "you see",
}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _best_input_device():
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if d["max_input_channels"] > 0:
            if any(k in d["name"].lower() for k in ("built-in", "macbook", "internal")):
                return i
    for i, d in enumerate(devices):
        if d["max_input_channels"] > 0:
            return i
    return None


def _load_snippets() -> dict:
    if not os.path.exists(SNIPPETS_FILE):
        defaults = {"my email": "your@email.com", "sign off": "Best regards,\n"}
        with open(SNIPPETS_FILE, "w") as f:
            json.dump(defaults, f, indent=2)
        return defaults
    with open(SNIPPETS_FILE) as f:
        return json.load(f)


def _load_dictionary() -> list:
    if not os.path.exists(DICT_FILE):
        with open(DICT_FILE, "w") as f:
            f.write("# Add custom words below, one per line\n")
        return []
    with open(DICT_FILE) as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


# Backtrack ("scratch that") — modelled on Wispr Flow's phrase list.
# Hard phrases discard the sentence/clause spoken before them.
# Soft phrases ("no wait") swap the last few words for what follows.
# "actually" / "i mean" are left out: too common in normal speech without an LLM.
BACKTRACK_HARD = ["scratch that", "never mind", "nevermind", "forget that",
                  "cancel that", "strike that", "delete that"]
BACKTRACK_SOFT = ["no wait", "wait no", "sorry i meant", "i meant"]


def _apply_backtrack(text: str) -> str:
    hard = "|".join(re.escape(p) for p in BACKTRACK_HARD)
    soft = "|".join(re.escape(p) for p in BACKTRACK_SOFT)
    pattern = re.compile(rf"[,.;!?]?\s*\b(?:(?P<hard>{hard})|(?P<soft>{soft}))\b[,.;!?]?\s*",
                         re.IGNORECASE)
    while (m := pattern.search(text)):
        before, after = text[:m.start()].rstrip(), text[m.end():].lstrip()
        if m.group("hard"):
            # Drop back to the previous sentence boundary.
            cut = max(before.rfind(c) for c in ".!?")
            before = before[:cut + 1] if cut >= 0 else ""
        else:
            # Replace as many trailing words as the correction's first clause has (max 3).
            fix = after.split()[:3]
            words = before.split()
            nums = [i for i, w in enumerate(words) if re.match(r"[\d$£€]", w)]
            if fix and re.match(r"[\d$£€]", fix[0]) and nums:
                # Number correction ("3 p.m., no wait, 4 p.m.") replaces from the last number on.
                before = " ".join(words[:nums[-1]])
            else:
                n = min(max(len(re.split(r"[,;!?]|\.\s", after, 1)[0].split()), 1), 3)
                before = " ".join(words[:-n]) if len(words) > n else ""
        text = f"{before} {after}".strip()
    return text


def _clean_text(text: str) -> str:
    text = _apply_backtrack(text)
    for phrase in sorted([fw for fw in FILLER_WORDS if " " in fw], key=len, reverse=True):
        text = re.sub(rf"\b{re.escape(phrase)}\b[,]?\s*", "", text, flags=re.IGNORECASE)
    for word in [fw for fw in FILLER_WORDS if " " not in fw]:
        text = re.sub(rf"^{re.escape(word)}[,]?\s+", "", text, flags=re.IGNORECASE)
    if text:
        text = text[0].upper() + text[1:]
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def _apply_snippets(text: str, snippets: dict) -> str:
    lower = text.lower().strip().rstrip(".")
    for trigger, expansion in snippets.items():
        if lower == trigger.lower():
            return expansion
    return text


def _paste_on_main(text: str):
    """Clipboard + ⌘V, then restore the old clipboard. Must run on the main thread:
    macOS terminates apps that query keyboard/input-source APIs off the main queue."""
    from AppKit import NSPasteboard, NSPasteboardTypeString
    import Quartz
    pb = NSPasteboard.generalPasteboard()
    old = pb.stringForType_(NSPasteboardTypeString)
    pb.clearContents()
    pb.setString_forType_(text, NSPasteboardTypeString)
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    for down in (True, False):
        ev = Quartz.CGEventCreateKeyboardEvent(src, 9, down)          # 9 = "v"
        Quartz.CGEventSetFlags(ev, Quartz.kCGEventFlagMaskCommand)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)

    def restore():
        if old is not None:
            pb.clearContents()
            pb.setString_forType_(old, NSPasteboardTypeString)
    from PyObjCTools import AppHelper
    AppHelper.callLater(0.6, restore)


def _type_text(text: str):
    time.sleep(TYPING_DELAY)            # let the hotkey release settle
    from PyObjCTools import AppHelper
    AppHelper.callAfter(_paste_on_main, text)


# ─── Store (history, dictionary, snippets for the main window) ──────────────

class Store:
    """Persists dictation history and serves state to the main window."""

    def __init__(self, core):
        self.core = core
        self._lock = threading.Lock()
        try:
            with open(HISTORY_FILE) as f:
                self.history = json.load(f)
        except (OSError, ValueError):
            self.history = []

    def _save_history(self):
        with open(HISTORY_FILE, "w") as f:
            json.dump(self.history[-5000:], f)

    def add(self, text, seconds):
        with self._lock:
            self.history.append({"ts": time.time(), "text": text,
                                 "words": len(text.split()), "secs": round(seconds, 2)})
            self._save_history()

    def clear_history(self):
        with self._lock:
            self.history = []
            self._save_history()

    def save_dictionary(self, words):
        with open(DICT_FILE, "w") as f:
            f.write("# Add custom words below, one per line\n" + "\n".join(words) + "\n")
        self.core.reload_config()

    def save_snippets(self, snippets):
        with open(SNIPPETS_FILE, "w") as f:
            json.dump(snippets, f, indent=2, ensure_ascii=False)
        self.core.reload_config()

    def state(self):
        with self._lock:
            hist = list(self.history[-300:])
            words = sum(e["words"] for e in self.history)
            secs = sum(e["secs"] for e in self.history)
            days = {time.strftime("%Y-%m-%d", time.localtime(e["ts"])) for e in self.history}
        # Streak: consecutive days with dictation, ending today (or yesterday).
        streak, t = 0, time.time()
        if time.strftime("%Y-%m-%d", time.localtime(t)) not in days:
            t -= 86400
        while time.strftime("%Y-%m-%d", time.localtime(t)) in days:
            streak += 1
            t -= 86400
        return {"history": hist, "dictionary": self.core.dictionary, "snippets": self.core.snippets,
                "stats": {"words": words, "wpm": round(words / (secs / 60)) if secs > 1 else 0,
                          "streak": streak}}


# ─── Core ────────────────────────────────────────────────────────────────────

class DictationCore:
    def __init__(self, on_status_change=None):
        self.on_status_change = on_status_change or (lambda s, t: None)
        self.model     = None
        self.recording = False
        self._lock     = threading.Lock()
        self.model_lock = threading.Lock()          # dictation and Notetaker share one model
        self._cancel   = False
        self.snippets   = _load_snippets()
        self.dictionary = _load_dictionary()
        self._initial_prompt = None
        self.on_level   = lambda rms: None          # live mic level for the pill
        self.on_result  = lambda text, secs: None   # finished dictation
        self.on_record_state = lambda recording: None   # sounds, mute, pause media
        self.language = lambda: LANGUAGE                 # Settings → System → Language

    def reload_config(self):
        self.snippets   = _load_snippets()
        self.dictionary = _load_dictionary()
        self._initial_prompt = ", ".join(self.dictionary) if self.dictionary else None
        self.on_status_change(ICON_IDLE, "Config reloaded ✓")

    def load_model(self):
        self.on_status_change(ICON_LOADING, "Loading model… (first run may take a minute)")
        try:
            self._initial_prompt = ", ".join(self.dictionary) if self.dictionary else None
            self.model = WhisperModel(MODEL_PATH or MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE)
            # Warm-up: the first transcription is much slower (memory allocation, caches),
            # so pay that cost now instead of on the first dictation.
            warm = (0.01 * np.random.default_rng(0).standard_normal(16000)).astype(np.float32)
            list(self.model.transcribe(warm, language="en", **DECODE)[0])
            self.on_status_change(ICON_IDLE, "Ready — hold ⌥ Right to dictate")
        except Exception as e:
            self.on_status_change(ICON_ERROR, f"Model load failed: {e}")

    def start_recording(self):
        with self._lock:
            if self.recording or self.model is None:
                return
            self.recording = True
            self._cancel = False
        self.on_record_state(True)
        self.on_status_change(ICON_RECORDING, "Recording…")
        threading.Thread(target=self._record_loop, daemon=True).start()

    def stop_recording(self):
        with self._lock:
            self.recording = False

    def cancel_recording(self):
        """Stop without transcribing (e.g. the hotkey was part of another shortcut)."""
        with self._lock:
            self._cancel = True
            self.recording = False

    def _record_loop(self):
        frames, device = [], _best_input_device()
        try:
            with sd.InputStream(device=device, samplerate=SAMPLE_RATE,
                                channels=1, dtype="float32", blocksize=1024) as stream:
                while self.recording:
                    data, _ = stream.read(1024)
                    frames.append(data.copy())
                    self.on_level(float(np.sqrt(np.mean(data ** 2))))
        except Exception as e:
            self.on_record_state(False)
            self.on_status_change(ICON_ERROR, f"Mic error: {e}")
            return
        self.on_record_state(False)

        if not frames or self._cancel:
            self.on_status_change(ICON_IDLE, "Ready — hold ⌥ Right to dictate")
            return

        audio = np.concatenate(frames, axis=0).flatten()
        if len(audio) / SAMPLE_RATE < MIN_DURATION:
            self.on_status_change(ICON_IDLE, "Ready — hold ⌥ Right to dictate")
            return

        self._transcribe(audio)

    def _transcribe(self, audio):
        self._secs = len(audio) / SAMPLE_RATE
        self.on_status_change(ICON_TRANSCRIBING, "Transcribing…")
        try:
            with self.model_lock:      # segments is lazy: consume it while holding the lock
                segments, _ = self.model.transcribe(
                    audio, language=self.language(),
                    initial_prompt=self._initial_prompt,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=300),
                    **DECODE,
                )
                raw = " ".join(s.text for s in segments).strip()
            text = _clean_text(raw)
            text = _apply_snippets(text, self.snippets)
            if text:
                self.on_result(text, self._secs)   # save first: history is the backup if pasting fails
                _type_text(text)
                self.on_status_change(ICON_IDLE, f"✓ {text[:50]}{'…' if len(text)>50 else ''}")
            else:
                self.on_status_change(ICON_IDLE, "Ready — hold ⌥ Right to dictate")
        except Exception as e:
            self.on_status_change(ICON_ERROR, f"Error: {e}")

    def transcribe_meeting(self, audio):
        """Transcribe one Notetaker chunk. Keeps the speaker's words as said:
        no backtrack, snippets or filler removal."""
        with self.model_lock:
            segments, _ = self.model.transcribe(
                audio, language=self.language(), initial_prompt=self._initial_prompt,
                vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500), **DECODE)
            return clean_transcript((s.text, s.no_speech_prob, s.avg_logprob, s.compression_ratio)
                                    for s in segments)


# ─── Hotkey ──────────────────────────────────────────────────────────────────

class HotkeyListener:
    """Hold-to-talk on Right Option, plus the Notetaker shortcut (default ⌥M).

    The shortcut is swallowed so it doesn't also type a character (⌥M = µ)."""

    def __init__(self, core, settings=None, on_shortcut=None):
        self.core, self._held = core, False
        self.settings = settings
        self.on_shortcut = on_shortcut
        self.paused = False             # True while Settings is recording a new shortcut

    def restart(self):
        if getattr(self, "_listener", None) is not None:
            self._listener.stop()
        self._held = False
        self.start()

    def start(self):
        kwargs = {}
        if self.settings is not None and self.on_shortcut is not None:
            kwargs["darwin_intercept"] = self._intercept
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release, **kwargs)
        self._listener.daemon = True
        self._listener.start()

    def _intercept(self, event_type, event):
        import Quartz
        if self.paused or event_type not in (Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp):
            return event
        try:
            from system import shortcut_matches
            keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            if not shortcut_matches(self.settings["meeting_shortcut"], keycode, Quartz.CGEventGetFlags(event)):
                return event
            if event_type == Quartz.kCGEventKeyDown and not Quartz.CGEventGetIntegerValueField(
                    event, Quartz.kCGKeyboardEventAutorepeat):
                if self._held:                  # Right ⌥ was the shortcut's modifier, not dictation
                    self._held = False
                    self.core.cancel_recording()
                from PyObjCTools import AppHelper
                AppHelper.callAfter(self.on_shortcut)
            return None
        except Exception as e:
            print(f"Shortcut error: {e}", flush=True)
            return event

    def _on_press(self, key):
        if key == HOTKEY and not self._held:
            self._held = True
            self.core.start_recording()

    def _on_release(self, key):
        if key == HOTKEY and self._held:
            self._held = False
            self.core.stop_recording()


# ─── Menu Bar ────────────────────────────────────────────────────────────────

if HAS_RUMPS:
    import objc
    import ui
    import macos
    import meetings
    import system
    from notes import NotesStore
    from notetaker import Notetaker
    from settings import Settings, options as setting_options

    def _clock(secs):
        secs = int(secs)
        h, m, s = secs // 3600, secs // 60 % 60, secs % 60
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    class MenuBarApp(rumps.App):
        def __init__(self):
            super().__init__("Dictation", title=None, quit_button=None)
            self.settings = Settings(SETTINGS_FILE)
            self.notes = NotesStore(NOTES_DIR)
            self.notes.recover_interrupted()
            self._status = rumps.MenuItem("Loading model…")
            self._notes_item = rumps.MenuItem("Start Notetaker", callback=lambda _: self.toggle_notetaker())
            self._meeting_item = rumps.MenuItem("No upcoming meetings")
            self.menu = [
                rumps.MenuItem("Open Dictation", callback=lambda _: self._open_window()),
                rumps.MenuItem("New Note", callback=lambda _: self._new_note()),
                self._notes_item,
                rumps.MenuItem("Copy Last Dictation", callback=lambda _: self._copy_last()),
                None,
                self._meeting_item,
                None,
                self._status,
                None,
                rumps.MenuItem("Quit", callback=lambda _: self._quit()),
            ]
            self._pill = self._window = self._notepad = self._toast = None
            self._error_mark = None
            self._title_text = None
            self._apply_status(ICON_LOADING, "Loading model…")
            self.core   = DictationCore(on_status_change=self._set_status)
            self.store  = Store(self.core)
            self.core.on_level  = self._on_level
            self.core.on_result = self._on_result
            self.core.on_record_state = self._on_record_state
            self.core.language = lambda: whisper_language(self.settings["dictation_language"])
            self.ducker = macos.AudioDucker()

            # Notetaker and meeting detection
            self.notetaker = Notetaker(
                transcribe=self.core.transcribe_meeting,
                on_segment=self._on_segment,
                on_stopped=lambda nid, dur, reason: ui.on_main(self._notetaker_stopped, nid, dur, reason),
                on_warning=lambda nid, left: ui.on_main(self._notetaker_warning, left),
                on_error=lambda msg: ui.on_main(self._notetaker_error, msg),
                system_audio=macos.SystemAudioCapture,
                device=_best_input_device)
            self.calendar = macos.Calendar()
            self.notifier = meetings.MeetingNotifier()
            self.calls = meetings.CallTracker()
            self._events, self._events_at, self._cal_status = [], 0.0, None
            self._next = None
            self._notes_from_call = False
            self._shown_errors = set()
            self._quitting = False
            self._ticks = 0

            self.hotkey = HotkeyListener(self.core, self.settings, self.toggle_notetaker)
            threading.Thread(target=self.core.load_model, daemon=True).start()
            self.hotkey.start()
            ui.on_main(self._startup)
            self._ax_item = rumps.MenuItem("⚠️ Allow Accessibility…", callback=lambda _: self._open_ax())
            self._ax_ok = None
            self._ax_timer = rumps.Timer(self._check_ax, 2)
            self._ax_timer.start()
            self._tick_timer = rumps.Timer(self._tick, 1)
            self._tick_timer.start()

        def _startup(self):
            ui.install_edit_menu()
            self._install_reopen_handler()
            self._apply_settings(list(self.settings.all()), startup=True)
            self._update_menu()
            self._open_window()                  # show the window once at launch

        def _install_reopen_handler(self):
            """Clicking the Dock icon (when shown) reopens the main window."""
            app = self

            def reopen(_delegate, _sender, _visible):
                app._open_window()
                return True
            try:
                objc.classAddMethods(rumps.rumps.NSApp, [objc.selector(
                    reopen, selector=b"applicationShouldHandleReopen:hasVisibleWindows:", signature=b"Z@:@Z")])
            except Exception as e:
                print(f"Dock reopen handler: {e}", flush=True)

        def _check_ax(self, _=None):
            # Without Accessibility the hotkey is silently ignored, so say so in the menu.
            from ApplicationServices import AXIsProcessTrusted
            ok = bool(AXIsProcessTrusted())
            if ok == self._ax_ok:
                return
            if self._ax_ok is None and not ok:
                from ApplicationServices import AXIsProcessTrustedWithOptions
                AXIsProcessTrustedWithOptions({"AXTrustedCheckOptionPrompt": True})
            self._ax_ok = ok
            print(f"Accessibility trusted: {ok}", flush=True)
            if ok:
                if "⚠️ Allow Accessibility…" in self.menu:
                    del self.menu["⚠️ Allow Accessibility…"]
                # The key listener only receives events if started after trust is granted.
                self.hotkey.restart()
            elif "⚠️ Allow Accessibility…" not in self.menu:
                self.menu.insert_before("Open Dictation", self._ax_item)

        def _open_ax(self):
            os.system('open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"')

        # Menu-bar circle matching the app icon. Black PNGs are template images
        # (macOS tints them for light/dark); the red recording dot is not.
        _ICONS = {
            ICON_IDLE:         ("idle.png", True, None),
            ICON_LOADING:      ("busy.png", True, None),
            ICON_TRANSCRIBING: ("busy.png", True, None),
            ICON_RECORDING:    ("recording.png", False, None),
            ICON_ERROR:        ("busy.png", True, "!"),
        }

        def _set_status(self, icon, msg):
            # Called from worker threads; AppKit must be touched on the main thread.
            ui.on_main(self._apply_status, icon, msg)

        def _apply_status(self, icon, msg):
            png, template, mark = self._ICONS.get(icon, ("idle.png", True, None))
            self.template = template
            self.icon = os.path.join(RES_DIR, "menubar", png)
            self._error_mark = mark
            self._refresh_title()
            self._status.title = msg
            if icon in (ICON_RECORDING, ICON_TRANSCRIBING):
                self._ensure_pill().show_("record" if icon == ICON_RECORDING else "busy")
            elif self._pill is not None:
                self._pill.hide()

        def _ensure_pill(self):
            if self._pill is None:
                self._pill = ui.Pill.alloc().init()
                self._pill.always = self.settings["show_bar_always"]
                macos.set_hidden_from_capture(self._pill.panel, self.settings["hide_from_screen_capture"])
            return self._pill

        def _refresh_title(self):
            parts = [self._error_mark] if self._error_mark else []
            if getattr(self, "notetaker", None) is not None and self.notetaker.active:
                parts.append("● " + _clock(self.notetaker.elapsed()))
            elif getattr(self, "settings", None) is not None and self.settings["show_next_meeting"] \
                    and getattr(self, "_next", None):
                parts.append(meetings.menubar_text(self._next, time.time()))
            text = " ".join(parts) or None
            if text != self._title_text:
                self._title_text = text
                self.title = text

        def _on_level(self, rms):
            if self._pill is not None:
                self._pill.level = rms           # plain float; read by the pill's timer

        def _on_record_state(self, recording):
            # Dictation started/stopped (worker thread): sounds, mute, pause media.
            if self.settings["sounds"]:
                ui.on_main(macos.play_sound, "Tink" if recording else "Pop")
            if recording:
                self.ducker.begin(self.settings["mute_while_dictating"],
                                  self.settings["pause_media_while_dictating"])
            else:
                self.ducker.end()

        def _on_result(self, text, secs):
            self.store.add(text, secs)
            ui.on_main(self._refresh_windows)

        def _copy_last(self):
            if self.store.history:
                self._copy(self.store.history[-1]["text"])

        def _copy(self, text):
            from AppKit import NSPasteboard, NSPasteboardTypeString
            pb = NSPasteboard.generalPasteboard()
            pb.clearContents()
            pb.setString_forType_(text, NSPasteboardTypeString)

        # ── Windows ──

        def _open_window(self, page=None, note_id=None):
            if self._window is None:
                self._window = ui.WebWindow.alloc().initWithApp_html_mode_(self, WEB_HTML, "main")
            if note_id:
                self._window.bridge.note_id = note_id
            if page:
                self._window.bridge.goto = page
            self._window.show()

        def _open_notepad(self, note_id=None):
            if self._notepad is None:
                self._notepad = ui.WebWindow.alloc().initWithApp_html_mode_(self, WEB_HTML, "notepad")
                macos.set_hidden_from_capture(self._notepad.win, self.settings["hide_from_screen_capture"])
            if note_id:
                self._notepad.bridge.note_id = note_id
            self._notepad.show()

        def _refresh_windows(self, skip=None):
            for w in (self._window, self._notepad):
                if w is not None and w.bridge is not skip:
                    w.refresh()

        def _new_note(self):
            note = self.notes.create("")
            self._open_window(page="notes", note_id=note["id"])

        # ── Toasts ──

        def _show_toast(self, title, body, buttons, timeout=20, sound=True):
            if self._toast is not None:
                self._toast.close()
            t = ui.Toast.alloc().initWithTitle_body_buttons_(title, body, buttons)
            macos.set_hidden_from_capture(t.panel, self.settings["hide_from_screen_capture"])

            def closed(tt):
                if self._toast is tt:
                    self._toast = None
            t.on_close = closed
            self._toast = t
            t.show_(timeout)
            if sound and self.settings["sounds"]:
                macos.play_sound("Glass")

        # ── Notetaker ──

        def toggle_notetaker(self):
            if self.notetaker.active:
                self.stop_notetaker()
            else:
                self.start_notetaker()

        def start_notetaker(self, title=None, from_call=False):
            if self.notetaker.active:
                self._open_notepad(self.notetaker.note_id)
                return
            if self.core.model is None:
                self._show_toast("Notetaker isn't ready yet", "The speech model is still loading. Try again in a moment.",
                                 [("OK", None)], timeout=8)
                return
            now = time.time()
            if not title:
                if self._next and abs(self._next["start"] - now) < 15 * 60:
                    title = self._next["title"]
                elif self.calls.in_call and self.calls.app:
                    title = f"{self.calls.app} call"
                else:
                    title = "Meeting notes"
            note = self.notes.create(title, meeting=True)
            self.notes.set_recording(note["id"], True)
            self._notes_from_call = from_call or self.calls.in_call
            self.notetaker.start(note["id"], self.settings["max_recording_minutes"] * 60,
                                 capture_system=self.settings["capture_system_audio"])
            if self.settings["sounds"]:
                macos.play_sound("Tink")
            if self.settings["open_notepad_on_start"] or self.settings["split_screen_on_join"]:
                self._open_notepad(note["id"])
                if self.settings["split_screen_on_join"]:
                    macos.split_screen(macos.find_meeting_app(self.calls.app if self.calls.in_call else None),
                                       self._notepad.win)
            self._update_menu()
            self._refresh_title()
            self._refresh_windows()

        def stop_notetaker(self, reason="user"):
            self.notetaker.stop(reason)

        def _on_segment(self, note_id, start, text):
            self.notes.append_transcript(note_id, start, text)
            ui.on_main(self._refresh_windows)

        def _notetaker_stopped(self, note_id, duration, reason):
            self.notes.set_recording(note_id, False, duration)
            self._notes_from_call = False
            self._update_menu()
            self._refresh_title()
            self._refresh_windows()
            if self._quitting:
                rumps.quit_application()
                return
            note = self.notes.get(note_id) or {}
            why = {"max_length": "Stopped at the maximum recording length. ",
                   "call_ended": "Stopped because the call ended. ",
                   "error": "Stopped because the microphone failed. "}.get(reason, "")
            self._show_toast("Meeting notes saved", f"{why}{note.get('title') or 'Untitled'} · {_clock(duration)}",
                             [("Open", lambda: self._open_window(page="notes", note_id=note_id)),
                              ("Dismiss", None)], timeout=15, sound=False)
            if self.settings["sounds"]:
                macos.play_sound("Pop")

        def _notetaker_warning(self, secs_left):
            mins = max(1, round(secs_left / 60))
            limit = dict(setting_options()["max_recording_minutes"]).get(
                self.settings["max_recording_minutes"], "")
            self._show_toast(f"Notetaker stops in {mins} minute{'s' if mins != 1 else ''}",
                             f"Recordings are limited to {limit}. You can change this in Settings → Notetaker.",
                             [("OK", None)], timeout=20)

        def _notetaker_error(self, msg):
            print(msg, flush=True)
            if msg in self._shown_errors:
                return
            self._shown_errors.add(msg)
            self._show_toast("Notetaker", msg, [("OK", None)], timeout=20)

        def _update_menu(self):
            label = self.settings["meeting_shortcut"]["label"]
            self._notes_item.title = "Stop Notetaker" if self.notetaker.active else f"Start Notetaker ({label})"

        # ── Once a second: calendar, heads-up, call detection, menu-bar text ──

        def _tick(self, _=None):
            self._ticks += 1
            now = time.time()
            s = self.settings
            wants_calendar = s["notify_before_meeting"] >= 0 or s["show_next_meeting"]
            if wants_calendar:
                if now - self._events_at > 60 or self.calendar.status != self._cal_status:
                    self._events = self.calendar.events(now)
                    self._events_at = now
                    self._cal_status = self.calendar.status
            else:
                self._events = []
            self._next = meetings.next_meeting(self._events, now)
            self._update_meeting_item(now)

            for e in self.notifier.due(self._events, now, s["notify_before_meeting"]):
                if self.notetaker.active:
                    continue
                left = e["start"] - now
                when = "is starting" if left <= 1 else f"starts {meetings.format_countdown(left)}"
                title = e["title"]
                self._show_toast(f"{title} {when}", "Start the Notetaker to transcribe it. Always ask for consent first.",
                                 [("Take notes", lambda t=title: self.start_notetaker(title=t)), ("Dismiss", None)],
                                 timeout=30)

            if self._ticks % 2 == 0 and (s["auto_detect_calls"] or
                                          (self.notetaker.active and s["stop_when_call_ends"])):
                r = macos.mic_used_by_other_app(self_using_mic=self.core.recording or self.notetaker.active)
                if r is not None:
                    event = self.calls.update(r[0], now, r[1])
                    if event == "started" and s["auto_detect_calls"] and not self.notetaker.active:
                        where = f" in {self.calls.app}" if self.calls.app else ""
                        self._show_toast(f"Call detected{where}", "Take notes for this call? Always ask for consent first.",
                                         [("Take notes", lambda: self.start_notetaker(from_call=True)),
                                          ("Not now", None)], timeout=25)
                    elif event == "ended" and self.notetaker.active and self._notes_from_call \
                            and s["stop_when_call_ends"]:
                        self.stop_notetaker("call_ended")
            self._refresh_title()

        def _update_meeting_item(self, now):
            e = self._next
            if e is None:
                text = ("Allow Calendar access for meetings…" if self.calendar.status == "denied"
                        else "No upcoming meetings")
                cb = (lambda _: os.system('open "x-apple.systempreferences:com.apple.preference.security?Privacy_Calendars"')) \
                    if self.calendar.status == "denied" else None
            else:
                at = time.strftime("%I:%M %p", time.localtime(e["start"])).lstrip("0").lower()
                text = f"{e['title']} · {at} — Take notes"
                cb = lambda _, t=e["title"]: self.start_notetaker(title=t)
            if self._meeting_item.title != text:
                self._meeting_item.title = text
                self._meeting_item.set_callback(cb)

        # ── Settings ──

        def _apply_settings(self, keys, startup=False):
            s = self.settings
            for k in keys:
                v = s[k]
                if k == "launch_at_login" and (v or not startup):
                    macos.set_launch_at_login(v, FROZEN, sys.executable, os.path.abspath(__file__))
                elif k == "show_in_dock" and (v or not startup):
                    macos.set_dock_icon(v)
                elif k == "show_bar_always" and (v or not startup):
                    self._ensure_pill().set_always(v)
                elif k == "hide_from_screen_capture":
                    for w in (self._pill and self._pill.panel, self._notepad and self._notepad.win,
                              self._toast and self._toast.panel):
                        if w:
                            macos.set_hidden_from_capture(w, v)
                elif k in ("notify_before_meeting", "show_next_meeting"):
                    self._events_at = 0
                elif k == "meeting_shortcut":
                    self._update_menu()

        # ── Messages from the web pages ──

        def state_for(self, bridge):
            st = self.store.state()
            st["settings"] = self.settings.all()
            st["options"] = setting_options()
            st["notes"] = self.notes.summaries()
            if bridge.mode == "notepad" and self.notetaker.active:
                bridge.note_id = self.notetaker.note_id
            st["note"] = self.notes.get(bridge.note_id) if bridge.note_id else None
            st["notetaker"] = {"active": self.notetaker.active, "note_id": self.notetaker.note_id,
                               "started_at": time.time() - self.notetaker.elapsed()}
            st["calendar"] = self.calendar.status
            st["glass"] = True                    # the window has native frosted glass behind the page
            st["goto"], bridge.goto = getattr(bridge, "goto", None), None
            return st

        def handle_message(self, msg, bridge):
            """Runs a button's action. Failures are shown and logged instead of failing silently."""
            try:
                return self._handle_message(msg, bridge)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._show_toast("That didn't work", f"{msg.get('type')}: {e}", [("OK", None)], timeout=15)
                return False

        def _handle_message(self, msg, bridge):
            """Returns False when the sender doesn't need a re-render."""
            kind = msg.get("type")
            if kind == "saveDictionary":
                self.store.save_dictionary([str(w) for w in msg.get("words", [])])
            elif kind == "saveSnippets":
                self.store.save_snippets({str(k): str(v) for k, v in dict(msg.get("snippets", {})).items()})
            elif kind == "clearHistory":
                self.store.clear_history()
            elif kind == "saveSettings":
                changed = self.settings.update(dict(msg.get("changes", {})))
                self._apply_settings(changed)
                self._refresh_windows()
                return False
            elif kind == "captureShortcut":
                self.hotkey.paused = bool(msg.get("on"))
                return False
            elif kind == "setShortcut":
                self.hotkey.paused = False
                sc = system.shortcut_from_js(str(msg.get("code", "")), list(msg.get("mods", [])))
                if sc and self.settings.update({"meeting_shortcut": sc}):
                    self._apply_settings(["meeting_shortcut"])
                self._refresh_windows()
                return False
            elif kind == "openNote":
                bridge.note_id = msg.get("id")
            elif kind == "newNote":
                bridge.note_id = self.notes.create(str(msg.get("title", "")))["id"]
                self._refresh_windows(skip=bridge)
            elif kind == "updateNote":
                self.notes.update(str(msg.get("id")), title=msg.get("title"), body=msg.get("body"))
                self._refresh_windows(skip=bridge)    # don't re-render the window being typed in
                return False
            elif kind == "deleteNote":
                nid = str(msg.get("id"))
                if nid != self.notetaker.note_id:
                    self.notes.delete(nid)
                    for b in (bridge, self._window and self._window.bridge, self._notepad and self._notepad.bridge):
                        if b is not None and b.note_id == nid:
                            b.note_id = None
                self._refresh_windows()
                return False
            elif kind == "copyNote":
                self._copy(self.notes.to_markdown(str(msg.get("id"))))
                return False
            elif kind == "exportNote":
                self._export_note(str(msg.get("id")))
                return False
            elif kind == "openNotepad":
                self._open_notepad(msg.get("id") or bridge.note_id)
                return False
            elif kind == "openMain":
                self._open_window(page="notes", note_id=msg.get("id"))
                return False
            elif kind == "startNotetaker":
                self.start_notetaker()
                return False
            elif kind == "stopNotetaker":
                self.stop_notetaker()
                return False
            elif kind == "openPrivacy":
                pane = {"calendar": "Privacy_Calendars", "screen": "Privacy_ScreenCapture",
                        "mic": "Privacy_Microphone"}.get(msg.get("pane"), "Privacy")
                os.system(f'open "x-apple.systempreferences:com.apple.preference.security?{pane}"')
                return False
            return True

        def _export_note(self, note_id):
            note = self.notes.get(note_id)
            if note is None:
                return
            from AppKit import NSSavePanel, NSApp as _NSApp
            panel = NSSavePanel.savePanel()
            name = re.sub(r'[/:\\]', "-", note["title"] or "Untitled note")
            panel.setNameFieldStringValue_(f"{name}.md")
            _NSApp.activateIgnoringOtherApps_(True)
            if panel.runModal() == 1:
                path = str(panel.URL().path())
                with open(path, "w") as f:
                    f.write(self.notes.to_markdown(note_id))
                self._show_toast("Note exported", path, [("OK", None)], timeout=6, sound=False)

        def _quit(self):
            if self.notetaker.active:
                # Let the last chunk transcribe and save, then quit (or give up after 15 s).
                self._quitting = True
                self.stop_notetaker()
                self._quit_timer = rumps.Timer(lambda _: rumps.quit_application(), 15)
                self._quit_timer.start()
            else:
                rumps.quit_application()


# ─── Entry ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Packaged app: stop multiprocessing helper processes from relaunching the whole app.
    import multiprocessing
    multiprocessing.freeze_support()
    if len(sys.argv) == 3 and sys.argv[1] == "--selftest":
        # Diagnostic: transcribe a 16 kHz mono WAV and print the result or traceback.
        import traceback, wave
        w = wave.open(sys.argv[2])
        audio = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        try:     # Notetaker frameworks are imported lazily; make sure the bundle has them
            import EventKit, ScreenCaptureKit, CoreMedia, dispatch  # noqa: F401
            print("FRAMEWORKS OK", flush=True)
        except Exception:
            traceback.print_exc()
        core = DictationCore(on_status_change=lambda i, m: print(i, m, flush=True))
        core.load_model()
        try:
            t = time.perf_counter()
            segs, _ = core.model.transcribe(audio, language=LANGUAGE, vad_filter=True,
                                            vad_parameters=dict(min_silence_duration_ms=300), **DECODE)
            text = _clean_text(" ".join(s.text for s in segs))
            print(f"TIME: {time.perf_counter() - t:.2f}s", flush=True)
            print("OUT:", text)
        except Exception:
            traceback.print_exc()
        sys.exit(0)
    if HAS_RUMPS:
        MenuBarApp().run()
    else:
        core   = DictationCore(on_status_change=lambda i, m: print(f"\r{i} {m:<60}", end="", flush=True))
        hotkey = HotkeyListener(core)
        threading.Thread(target=core.load_model, daemon=True).start()
        hotkey.start()
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            print("\nBye!")
