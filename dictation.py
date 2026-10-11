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

try:
    import rumps
    HAS_RUMPS = True
except ImportError:
    HAS_RUMPS = False

# ─── Paths ───────────────────────────────────────────────────────────────────

import sys

FROZEN = getattr(sys, "frozen", False)   # True inside the packaged .app
if FROZEN:
    # Bundle is read-only; user-editable files live in Application Support.
    APP_DIR = os.path.expanduser("~/Library/Application Support/Dictation")
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
WEB_HTML      = os.path.join(RES_DIR, "web", "index.html")

# ─── Config ──────────────────────────────────────────────────────────────────

SAMPLE_RATE  = 16000
HOTKEY       = keyboard.Key.alt_r   # Hold RIGHT OPTION ⌥
MODEL_SIZE   = "small"              # small = much better accuracy than base
LANGUAGE     = None                 # None = auto-detect (supports 100+ languages)
MIN_DURATION = 0.3
COMPUTE_TYPE = "int8"
TYPING_DELAY = 0.2

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
        self.snippets   = _load_snippets()
        self.dictionary = _load_dictionary()
        self._initial_prompt = None
        self.on_level   = lambda rms: None          # live mic level for the pill
        self.on_result  = lambda text, secs: None   # finished dictation

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
            self.on_status_change(ICON_IDLE, "Ready — hold ⌥ Right to dictate")
        except Exception as e:
            self.on_status_change(ICON_ERROR, f"Model load failed: {e}")

    def start_recording(self):
        with self._lock:
            if self.recording or self.model is None:
                return
            self.recording = True
        self.on_status_change(ICON_RECORDING, "Recording…")
        threading.Thread(target=self._record_loop, daemon=True).start()

    def stop_recording(self):
        with self._lock:
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
            self.on_status_change(ICON_ERROR, f"Mic error: {e}")
            return

        if not frames:
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
            segments, _ = self.model.transcribe(
                audio, language=LANGUAGE,
                initial_prompt=self._initial_prompt,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300),
            )
            text = _clean_text(" ".join(s.text for s in segments).strip())
            text = _apply_snippets(text, self.snippets)
            if text:
                self.on_result(text, self._secs)   # save first: history is the backup if pasting fails
                _type_text(text)
                self.on_status_change(ICON_IDLE, f"✓ {text[:50]}{'…' if len(text)>50 else ''}")
            else:
                self.on_status_change(ICON_IDLE, "Ready — hold ⌥ Right to dictate")
        except Exception as e:
            self.on_status_change(ICON_ERROR, f"Error: {e}")


# ─── Hotkey ──────────────────────────────────────────────────────────────────

class HotkeyListener:
    def __init__(self, core):
        self.core, self._held = core, False

    def restart(self):
        if getattr(self, "_listener", None) is not None:
            self._listener.stop()
        self._held = False
        self.start()

    def start(self):
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()

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
    import ui

    class MenuBarApp(rumps.App):
        def __init__(self):
            super().__init__("Dictation", title=None, quit_button="Quit")
            self._status = rumps.MenuItem("Loading model…")
            self.menu = [
                rumps.MenuItem("Open Dictation", callback=lambda _: self._open_window()),
                rumps.MenuItem("Copy Last Dictation", callback=lambda _: self._copy_last()),
                None,
                self._status,
                None,
            ]
            self._pill = self._window = None
            self._apply_status(ICON_LOADING, "Loading model…")
            self.core   = DictationCore(on_status_change=self._set_status)
            self.store  = Store(self.core)
            self.core.on_level  = self._on_level
            self.core.on_result = self._on_result
            self.hotkey = HotkeyListener(self.core)
            threading.Thread(target=self.core.load_model, daemon=True).start()
            self.hotkey.start()
            ui.on_main(self._open_window)
            self._ax_item = rumps.MenuItem("⚠️ Allow Accessibility…", callback=lambda _: self._open_ax())
            self._ax_ok = None
            self._ax_timer = rumps.Timer(self._check_ax, 2)
            self._ax_timer.start()

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
            os.system('open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"')        # show the window once at launch

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
            png, template, title = self._ICONS.get(icon, ("idle.png", True, None))
            self.template = template
            self.icon = os.path.join(RES_DIR, "menubar", png)
            self.title = title
            self._status.title = msg
            if icon in (ICON_RECORDING, ICON_TRANSCRIBING):
                if self._pill is None:
                    self._pill = ui.Pill.alloc().init()
                self._pill.show_("record" if icon == ICON_RECORDING else "busy")
            elif self._pill is not None:
                self._pill.hide()

        def _on_level(self, rms):
            if self._pill is not None:
                self._pill.level = rms           # plain float; read by the pill's timer

        def _on_result(self, text, secs):
            self.store.add(text, secs)
            ui.on_main(lambda: self._window and self._window.refresh())

        def _copy_last(self):
            if self.store.history:
                from AppKit import NSPasteboard, NSPasteboardTypeString
                pb = NSPasteboard.generalPasteboard()
                pb.clearContents()
                pb.setString_forType_(self.store.history[-1]["text"], NSPasteboardTypeString)

        def _open_window(self):
            if self._window is None:
                self._window = ui.MainWindow.alloc().initWithStore_html_(self.store, WEB_HTML)
            self._window.show()


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
        core = DictationCore(on_status_change=lambda i, m: print(i, m, flush=True))
        core.load_model()
        try:
            segs, _ = core.model.transcribe(audio, language=LANGUAGE, vad_filter=True,
                                            vad_parameters=dict(min_silence_duration_ms=300))
            print("OUT:", _clean_text(" ".join(s.text for s in segs)))
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
