"""Wiring test for the menu-bar app: loads dictation.py with macOS libraries stubbed
out and drives the bridge messages, Notetaker, meeting heads-up and call detection.

Run: python3 -m unittest discover -s tests
"""

import os
import sys
import tempfile
import threading
import time
import types
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _install_stubs():
    def mod(name, **attrs):
        m = types.ModuleType(name)
        m.__dict__.update(attrs)
        sys.modules[name] = m
        return m

    class Listener:
        def __init__(self, **kw):
            self.kw = kw
            self.daemon = False

        def start(self):
            pass

        def stop(self):
            pass

    keyboard = mod("pynput.keyboard", Key=types.SimpleNamespace(alt_r="alt_r"), Listener=Listener)
    mod("pynput", keyboard=keyboard)
    mod("faster_whisper", WhisperModel=object)
    mod("sounddevice", query_devices=lambda: [], InputStream=None)

    class MenuItem:
        def __init__(self, title, callback=None):
            self.title, self.callback = title, callback

        def set_callback(self, cb):
            self.callback = cb

    class Menu(list):
        def __contains__(self, title):
            return any(getattr(i, "title", None) == title for i in self)

    class App:
        def __init__(self, name, title=None, quit_button=None):
            self.title, self.icon, self.template = title, None, True
            self._menu = Menu()

        @property
        def menu(self):
            return self._menu

        @menu.setter
        def menu(self, items):
            self._menu = Menu(items)

    class Timer:
        def __init__(self, cb, interval):
            self.cb = cb

        def start(self):
            pass

    quits = []
    rumps = mod("rumps", App=App, MenuItem=MenuItem, Timer=Timer,
                quit_application=lambda: quits.append(1))
    rumps.rumps = types.SimpleNamespace(NSApp=object)
    rumps.quits = quits
    mod("objc", classAddMethods=lambda *a: None, selector=lambda *a, **k: None)

    class Pasteboard:
        text = None

        @classmethod
        def generalPasteboard(cls):
            return cls

        @classmethod
        def clearContents(cls):
            pass

        @classmethod
        def setString_forType_(cls, s, _t):
            cls.text = s

    class SavePanel:
        """NSSavePanel stand-in: 'saves' to SavePanel.path when it's set, else cancels."""
        path = None
        name = None

        @classmethod
        def savePanel(cls):
            return cls()

        def setNameFieldStringValue_(self, name):
            SavePanel.name = name

        def runModal(self):
            return 1 if SavePanel.path else 0

        def URL(self):
            return types.SimpleNamespace(path=lambda: SavePanel.path)

    mod("AppKit", NSPasteboard=Pasteboard, NSPasteboardTypeString="str", NSSavePanel=SavePanel,
        NSApp=types.SimpleNamespace(activateIgnoringOtherApps_=lambda flag: None))

    class Fake:
        """Stand-in for Pill / Toast / WebWindow objects."""
        made = []

        @classmethod
        def alloc(cls):
            return cls()

        def init(self):
            self.panel = object()
            return self

        def initWithTitle_body_buttons_(self, title, body, buttons):
            self.title, self.body, self.buttons = title, body, buttons
            self.panel = object()
            Fake.made.append(self)
            return self

        def initWithApp_html_mode_(self, app, html, mode):
            self.bridge = types.SimpleNamespace(mode=mode, note_id=None, goto=None, pushed=0)
            self.win = object()
            self.shown = 0
            return self

        def show(self):
            self.shown += 1

        def show_(self, *_):
            pass

        def hide(self):
            pass

        def set_always(self, v):
            self.always = v

        def refresh(self):
            self.bridge.pushed += 1

        def close(self):
            if getattr(self, "on_close", None):
                self.on_close(self)

    mod("ui", on_main=lambda fn, *a: fn(*a), Pill=Fake, Toast=Fake, WebWindow=Fake,
        install_edit_menu=lambda: None)
    return Fake, rumps


Fake, rumps_stub = _install_stubs()
import dictation  # noqa: E402
import macos  # noqa: E402

DATA_FILES = [("SETTINGS_FILE", "settings.json"), ("NOTES_DIR", "notes"), ("HISTORY_FILE", "history.json"),
              ("SNIPPETS_FILE", "snippets.json"), ("DICT_FILE", "dictionary.txt"),
              ("VOICE_TEST_DIR", "voice_test"), ("MODELS_DIR", "models")]


class FakeCalendar:
    status = "granted"
    evs = []

    def events(self, now, horizon=86400):
        return list(self.evs)


class FakeStream:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n):
        time.sleep(0.002)
        t = np.arange(n) / 16000
        return (0.1 * np.sin(2 * np.pi * 220 * t)).astype(np.float32).reshape(-1, 1), False


class AppWiringTest(unittest.TestCase):

    def setUp(self):
        self.calls = []
        self.mic = (False, None)
        p = self.patch
        data = tempfile.mkdtemp()
        for name, path in DATA_FILES:
            p(dictation, name, os.path.join(data, path))
        p(macos, "Calendar", FakeCalendar)
        p(macos, "mic_used_by_other_app", lambda self_using_mic: self.mic)
        p(macos, "play_sound", lambda name: self.calls.append(("sound", name)))
        p(macos, "set_hidden_from_capture", lambda w, h: self.calls.append(("hide", h)))
        p(macos, "set_launch_at_login", lambda *a: self.calls.append(("login", a[0])))
        p(macos, "set_dock_icon", lambda v: self.calls.append(("dock", v)))
        p(macos, "split_screen", lambda app, win: self.calls.append(("split", app)))
        p(macos, "find_meeting_app", lambda hint: hint)
        p(macos, "SystemAudioCapture", None)
        p(dictation.DictationCore, "load_model", lambda core, *a: setattr(core, "model", object()) or True)
        p(dictation.DictationCore, "transcribe_meeting", lambda core, audio: "hello from the meeting")
        Fake.made.clear()
        self.app = dictation.MenuBarApp()
        self.app.notetaker._input_stream = FakeStream
        self.app.notetaker._system_audio = None
        for t in threading.enumerate():
            if t.name != "MainThread" and t.is_alive() and "load_model" in repr(t):
                t.join(1)
        time.sleep(0.05)

    def patch(self, obj, name, value):
        old = getattr(obj, name)
        setattr(obj, name, value)
        self.addCleanup(setattr, obj, name, old)

    def bridge(self, mode="main"):
        return types.SimpleNamespace(mode=mode, note_id=None, goto=None)

    def test_startup_opens_window_and_state_is_complete(self):
        self.assertEqual(self.app._window.shown, 1)
        st = self.app.state_for(self.bridge())
        for key in ("history", "settings", "options", "notes", "note", "notetaker", "calendar"):
            self.assertIn(key, st)
        self.assertIn("Start Notetaker (⌥ M)", self.app._notes_item.title)

    def test_notes_messages(self):
        b = self.bridge()
        self.app.handle_message({"type": "newNote"}, b)
        nid = b.note_id
        self.assertIsNotNone(self.app.notes.get(nid))
        self.assertFalse(self.app.handle_message({"type": "updateNote", "id": nid, "title": "Plan", "body": "x"}, b))
        self.assertEqual(self.app.state_for(b)["note"]["title"], "Plan")
        self.app.handle_message({"type": "copyNote", "id": nid}, b)
        self.assertIn("# Plan", sys.modules["AppKit"].NSPasteboard.text)
        self.app.handle_message({"type": "deleteNote", "id": nid}, b)
        self.assertIsNone(self.app.notes.get(nid))
        self.assertIsNone(b.note_id)

    def test_settings_and_shortcut_messages(self):
        b = self.bridge()
        self.app.handle_message({"type": "saveSettings", "changes": {"show_in_dock": True, "show_bar_always": True,
                                                                     "launch_at_login": True}}, b)
        self.assertIn(("dock", True), self.calls)
        self.assertIn(("login", True), self.calls)
        self.assertTrue(self.app._pill.always)
        self.app.handle_message({"type": "captureShortcut", "on": True}, b)
        self.assertTrue(self.app.hotkey.paused)
        self.app.handle_message({"type": "setShortcut", "code": "KeyN", "mods": ["ctrl", "alt"]}, b)
        self.assertFalse(self.app.hotkey.paused)
        self.assertEqual(self.app.settings["meeting_shortcut"]["label"], "⌃⌥ N")
        self.assertIn("⌃⌥ N", self.app._notes_item.title)

    def wait_until(self, cond, timeout=5):
        end = time.time() + timeout
        while time.time() < end:
            if cond():
                return True
            time.sleep(0.02)
        return False

    def test_notetaker_start_transcribe_stop(self):
        self.app.settings.update({"split_screen_on_join": True})
        self.app.toggle_notetaker()
        nt = self.app.notetaker
        self.assertTrue(nt.active)
        self.assertIsNotNone(self.app._notepad)
        self.assertIn(("split", None), self.calls)
        self.assertEqual(self.app.state_for(self.app._notepad.bridge)["note"]["id"], nt.note_id)
        self.app._refresh_title()
        self.assertTrue(self.app.title.startswith("● 0:0"))
        nid = nt.note_id
        time.sleep(0.3)
        self.app.toggle_notetaker()
        self.assertTrue(self.wait_until(lambda: not nt.active))
        note = self.app.notes.get(nid)
        self.assertFalse(note["recording"])
        self.assertEqual(note["transcript"][0]["text"], "hello from the meeting")
        self.assertEqual(Fake.made[-1].title, "Meeting notes saved")

    def test_meeting_heads_up_and_menubar(self):
        now = time.time()
        FakeCalendar.evs = [{"id": "e1", "title": "Design review", "start": now + 10, "end": now + 1800,
                             "all_day": False}]
        self.addCleanup(setattr, FakeCalendar, "evs", [])
        self.app._tick()
        self.assertTrue(self.app.title.startswith("Design review · in "))
        self.assertTrue(Fake.made[-1].title.startswith("Design review starts in"))
        self.assertIn("Take notes", self.app._meeting_item.title)
        Fake.made[-1].buttons[0][1]()                   # "Take notes"
        self.assertTrue(self.wait_until(lambda: self.app.notetaker.active))
        self.assertEqual(self.app.notes.get(self.app.notetaker.note_id)["title"], "Design review")
        self.app.stop_notetaker()
        self.assertTrue(self.wait_until(lambda: not self.app.notetaker.active))

    def test_call_detected_then_ended_stops_notetaker(self):
        tracker = self.app.calls
        tracker.START_AFTER = tracker.END_AFTER = 0
        self.mic = (True, "zoom.us")
        self.app._ticks = 1
        self.app._tick()                                 # tick 2 → first sample flips immediately
        self.assertTrue(tracker.in_call)
        self.assertEqual(Fake.made[-1].title, "Call detected in zoom.us")
        Fake.made[-1].buttons[0][1]()
        self.assertTrue(self.app.notetaker.active)
        self.assertEqual(self.app.notes.get(self.app.notetaker.note_id)["title"], "zoom.us call")
        self.mic = (False, None)
        self.app._ticks = 1
        self.app._tick()
        self.assertTrue(self.wait_until(lambda: not self.app.notetaker.active))
        self.assertTrue(Fake.made[-1].body.startswith("Stopped because the call ended."))

    def test_dictation_sounds_and_ducking(self):
        events = []
        self.app.ducker = types.SimpleNamespace(begin=lambda m, p: events.append(("begin", m, p)),
                                                end=lambda: events.append("end"))
        self.app.settings.update({"mute_while_dictating": True})
        self.app._on_record_state(True)
        self.app._on_record_state(False)
        self.assertEqual(events, [("begin", True, False), "end"])
        self.assertIn(("sound", "Tink"), self.calls)
        self.assertIn(("sound", "Pop"), self.calls)


    def test_voice_test_record_run_score(self):
        app = self.app
        app.phrase_rec._input_stream = FakeStream
        b = self.bridge()
        app.handle_message({"type": "voiceTestRecord", "id": "gulf-4"}, b)
        self.assertEqual(app.state_for(b)["voicetest"]["recording"], "gulf-4")
        time.sleep(0.4)
        app.handle_message({"type": "voiceTestRecord", "id": "gulf-4"}, b)      # same button = stop
        st = app.state_for(b)["voicetest"]
        self.assertIsNone(st["recording"])
        self.assertTrue(next(p for p in st["phrases"] if p["id"] == "gulf-4")["recorded"])
        self.patch(dictation.DictationCore, "transcribe_raw", lambda core, audio: "الحين مشغول بكلمك بعدين")
        app.handle_message({"type": "voiceTestRun"}, b)
        self.assertTrue(self.wait_until(lambda: app._vt_progress is None))
        r = app.state_for(b)["voicetest"]["results"]
        self.assertEqual(r["accuracy"], 1.0)                                       # punctuation ignored
        self.assertEqual(r["per"]["gulf-4"]["heard"], "الحين مشغول بكلمك بعدين")
        self.assertEqual(Fake.made[-1].title, "Voice test finished")
        app.handle_message({"type": "voiceTestAdd", "text": "أبي قهوة"}, b)
        self.assertEqual(app.state_for(b)["voicetest"]["phrases"][-1]["text"], "أبي قهوة")

    def test_auto_language_picks_arabic_and_dialect_prompt(self):
        seen = {}

        class Seg:
            text = " كيفش"

        class FakeModel:
            def detect_language(self, audio, vad_filter=False):
                return "he", 0.5, [("he", 0.5), ("ar", 0.2), ("en", 0.25)]

            def transcribe(self, audio, **kw):
                seen.update(kw)
                return iter([Seg()]), None

        self.app.core.model = FakeModel()
        self.assertEqual(self.app.core.transcribe_raw(np.zeros(16000, np.float32)), "كيفش")
        self.assertEqual(seen["language"], "ar")
        self.assertIsNone(seen["initial_prompt"])                 # small model: no dialect primer
        self.app.core.dialect_prompt = True                       # large model
        self.app.core.transcribe_raw(np.zeros(16000, np.float32))
        self.assertIn("شحالش", seen["initial_prompt"])
        self.app.handle_message({"type": "saveSettings", "changes": {"dictation_language": "en"}}, self.bridge())
        self.app.core.transcribe_raw(np.zeros(16000, np.float32))
        self.assertEqual(seen["language"], "en")
        self.assertNotIn("شحالش", seen["initial_prompt"] or "")

    def test_choosing_accurate_model_downloads_then_loads_it(self):
        loaded, gate = [], threading.Event()

        def fake_download(name, folder):
            gate.wait(2)

        self.app.models._download = fake_download
        self.patch(dictation.DictationCore, "load_model",
                   lambda core, path=None, label=None, engine="cpu": loaded.append((path, label, engine)) or True)
        self.app.handle_message({"type": "saveSettings", "changes": {"speech_model": "turbo"}}, self.bridge())
        st = self.app.state_for(self.bridge())["model"]
        self.assertEqual((st["choice"], st["downloading"], st["ready"]), ("turbo", "turbo", False))
        gate.set()
        self.app.models._thread.join(2)
        self.assertTrue(loaded[-1][0].endswith("whisper-large-v3-turbo-mlx"))
        self.assertEqual(loaded[-1][1:], ("Whisper large-v3-turbo", "mlx"))
        self.app.handle_message({"type": "saveSettings", "changes": {"speech_model": "small"}}, self.bridge())
        for t in threading.enumerate():
            if t.name == "load_model":
                t.join(2)
        self.assertEqual(loaded[-1][1], "Whisper small")

    def test_every_ui_message_is_handled(self):
        """Each action the page can send has a handler (a typo would make a button do nothing)."""
        import re as _re
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "web", "index.html"), encoding="utf-8") as f:
            html = f.read()
        sent = set(_re.findall(r"type: '([A-Za-z]+)'", html))
        for pair in _re.findall(r"type: [\w.]+ \? '([A-Za-z]+)' : '([A-Za-z]+)'", html):    # toggles
            sent |= set(pair)
        with open(os.path.join(root, "dictation.py"), encoding="utf-8") as f:
            src = f.read()
        handled = set(_re.findall(r'kind == "([A-Za-z]+)"', src)) | {"copy", "ready"}   # copy/ready: ui.Bridge
        self.assertGreater(len(sent), 20)
        self.assertEqual(sent - handled, set())

    def test_buttons_do_what_they_say(self):
        """Every button's message, run through the app, changes what it should."""
        b, app = self.bridge(), self.app
        toasts = []
        self.patch(app, "_show_toast", lambda title, *a, **kw: toasts.append(title))
        AppKit = sys.modules["AppKit"]
        out = tempfile.mkdtemp()

        # Transcribe page: history and clear
        app.store.add("hello there", 1.0)
        self.assertEqual(len(app.state_for(b)["history"]), 1)
        app.handle_message({"type": "clearHistory"}, b)
        self.assertEqual(app.state_for(b)["history"], [])
        # Your words and Shortcuts
        app.handle_message({"type": "saveDictionary", "words": ["Kalam", "مسقط"]}, b)
        self.assertEqual(app.state_for(b)["dictionary"], ["Kalam", "مسقط"])
        app.handle_message({"type": "saveDictionary", "words": ["Kalam"]}, b)        # remove a word
        self.assertEqual(app.state_for(b)["dictionary"], ["Kalam"])
        app.handle_message({"type": "saveSnippets", "snippets": {"my email": "a@b.c"}}, b)
        self.assertEqual(app.state_for(b)["snippets"], {"my email": "a@b.c"})
        app.handle_message({"type": "saveSnippets", "snippets": {}}, b)              # remove a shortcut
        self.assertEqual(app.state_for(b)["snippets"], {})

        # Notes: new, open, open in Notepad / main window, export, delete
        app.handle_message({"type": "newNote"}, b)
        nid = b.note_id
        app.handle_message({"type": "updateNote", "id": nid, "title": "Plan: Q4", "body": "ship"}, b)
        other = self.bridge()
        app.handle_message({"type": "openNote", "id": nid}, other)
        self.assertEqual(app.state_for(other)["note"]["id"], nid)
        app.handle_message({"type": "openNotepad", "id": nid}, b)
        self.assertEqual(app._notepad.bridge.note_id, nid)
        app.handle_message({"type": "openMain", "id": nid}, b)
        self.assertEqual((app._window.bridge.note_id, app._window.bridge.goto), (nid, "notes"))
        AppKit.NSSavePanel.path = None                                            # cancelled: nothing written
        app.handle_message({"type": "exportNote", "id": nid}, b)
        self.assertEqual(AppKit.NSSavePanel.name, "Plan- Q4.md")
        AppKit.NSSavePanel.path = os.path.join(out, "plan.md")
        app.handle_message({"type": "exportNote", "id": nid}, b)
        with open(AppKit.NSSavePanel.path, encoding="utf-8") as f:
            self.assertIn("# Plan: Q4", f.read())
        self.assertIn("Note exported", toasts)
        app.handle_message({"type": "deleteNote", "id": nid}, b)
        self.assertIsNone(app.notes.get(nid))
        self.assertNotIn(nid, [n["id"] for n in app.state_for(b)["notes"]])
        for br in (b, app._notepad.bridge, app._window.bridge):
            self.assertIsNone(br.note_id)                      # no window keeps showing the deleted note

        # Notetaker buttons; the note being recorded can't be deleted until it stops
        app.handle_message({"type": "startNotetaker"}, b)
        self.assertTrue(app.notetaker.active)
        live = app.notetaker.note_id
        app.handle_message({"type": "deleteNote", "id": live}, b)
        self.assertIsNotNone(app.notes.get(live))
        app.handle_message({"type": "stopNotetaker"}, b)
        self.assertTrue(self.wait_until(lambda: not app.notetaker.active))
        app.handle_message({"type": "deleteNote", "id": live}, b)
        self.assertIsNone(app.notes.get(live))

        # Voice test: play, remove, export (cancelled and saved)
        played = []
        self.patch(macos, "play_file", played.append)
        pid = app.voicetest.data["phrases"][0]["id"]
        app.voicetest.save_recording(pid, np.zeros(8000, np.float32))
        app.handle_message({"type": "voiceTestPlay", "id": pid}, b)
        self.assertEqual(len(played), 1)
        AppKit.NSSavePanel.path = os.path.join(out, "voice-test.zip")
        app.handle_message({"type": "voiceTestExport"}, b)
        self.assertTrue(os.path.exists(AppKit.NSSavePanel.path))
        app.handle_message({"type": "voiceTestRemove", "id": pid}, b)
        self.assertIsNone(app.voicetest.phrase(pid))

        # Settings links and model retry
        opened = []
        self.patch(dictation.os, "system", opened.append)
        app.handle_message({"type": "openPrivacy", "pane": "calendar"}, b)
        self.assertIn("Privacy_Calendars", opened[-1])
        reloads = []
        self.patch(app, "_load_chosen_model", lambda: reloads.append(1))
        app.models.error = "no internet"
        app.handle_message({"type": "retryModel"}, b)
        self.assertEqual((reloads, app.models.error), ([1], None))
        self.assertEqual([t for t in toasts if "didn't work" in t], [])         # no action failed

    def test_menu_bar_items(self):
        app = self.app
        items = {i.title: i for i in app.menu if getattr(i, "title", None)}
        for title in ("Open Kalam", "New Note", "Copy Last Transcription", "Quit"):
            self.assertIn(title, items)
        items["Open Kalam"].callback(None)
        self.assertEqual(app._window.shown, 2)
        before = len(app.notes.summaries())
        items["New Note"].callback(None)
        self.assertEqual(len(app.notes.summaries()), before + 1)
        app.store.add("last thing I said", 1.0)
        items["Copy Last Transcription"].callback(None)
        self.assertEqual(sys.modules["AppKit"].NSPasteboard.text, "last thing I said")
        app._notes_item.callback(None)                                   # Start Notetaker
        self.assertTrue(app.notetaker.active)
        app._notes_item.callback(None)                                   # Stop
        self.assertTrue(self.wait_until(lambda: not app.notetaker.active))
        items["Quit"].callback(None)
        self.assertTrue(rumps_stub.quits)

    def test_language_setting(self):
        self.assertIsNone(self.app.core.language())                 # auto-detect by default
        self.app.handle_message({"type": "saveSettings", "changes": {"dictation_language": "en"}}, self.bridge())
        self.assertEqual(self.app.core.language(), "en")
        self.app.handle_message({"type": "saveSettings", "changes": {"dictation_language": "fr"}}, self.bridge())
        self.assertEqual(self.app.core.language(), "en")             # unknown values are ignored


class CleanTextTest(unittest.TestCase):
    """The full dictation clean-up (backtrack, fillers, punctuation) in both languages."""

    def test_english_unchanged_behaviour(self):
        c = dictation._clean_text
        self.assertEqual(c("um so meet at 3 p.m., no wait, 4 p.m."), "So meet at 4 p.m.")
        self.assertEqual(c("Send it today. Scratch that. Send it tomorrow."), "Send it tomorrow.")

    def test_arabic(self):
        c = dictation._clean_text
        self.assertEqual(c("اممم نلتقي الساعة ٣ ، لا لحظة ، الساعة ٤"), "نلتقي الساعة 4")
        self.assertEqual(c("أرسل التقرير اليوم. امسح هذا. أرسله بكرة ?"), "أرسله بكرة؟")
        self.assertEqual(c("مَرْحَباً يا فريق"), "مرحبا يا فريق")
        self.assertEqual(c("أبي ٣ نسخ قصدي ٥ نسخ"), "أبي 5 نسخ")
        self.assertEqual(c("نرسله لأحمد، لا أقصد، لسارة"), "نرسله لسارة")

    def test_english_more_corrections(self):
        c = dictation._clean_text
        self.assertEqual(c("let's meet at 3, no wait, at 4"), "Let's meet at 4")
        self.assertEqual(c("send it to John, no wait, to Sarah"), "Send it to Sarah")


class DataMigrationTest(unittest.TestCase):
    """First launch of Kalam copies (never moves) the newest earlier build's data."""

    def test_copies_from_dictation_2_first(self):
        import tempfile
        support = tempfile.mkdtemp()
        for name, text in (("Dictation", "old"), ("Dictation 2", "newer")):
            os.makedirs(os.path.join(support, name, "notes"))
            with open(os.path.join(support, name, "history.json"), "w") as f:
                f.write(text)
        with open(os.path.join(support, "Dictation 2", "notes", "n1.json"), "w") as f:
            f.write("{}")
        with open(os.path.join(support, "Dictation 2", "dictation.log"), "w") as f:
            f.write("log")
        kalam = os.path.join(support, "Kalam")
        dictation._copy_from_original(kalam, support)
        with open(os.path.join(kalam, "history.json")) as f:
            self.assertEqual(f.read(), "newer")
        self.assertTrue(os.path.exists(os.path.join(kalam, "notes", "n1.json")))
        self.assertFalse(os.path.exists(os.path.join(kalam, "dictation.log")))
        self.assertTrue(os.path.exists(os.path.join(support, "Dictation 2", "history.json")))   # left in place
        with open(os.path.join(kalam, "history.json"), "w") as f:
            f.write("mine")
        dictation._copy_from_original(kalam, support)                 # later launches never overwrite
        with open(os.path.join(kalam, "history.json")) as f:
            self.assertEqual(f.read(), "mine")


if __name__ == "__main__":
    unittest.main()
