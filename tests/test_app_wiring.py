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

    mod("AppKit", NSPasteboard=Pasteboard, NSPasteboardTypeString="str")

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
              ("SNIPPETS_FILE", "snippets.json"), ("DICT_FILE", "dictionary.txt")]


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
        p(dictation.DictationCore, "load_model", lambda core: setattr(core, "model", object()))
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


    def test_language_setting(self):
        self.assertIsNone(self.app.core.language())                 # auto-detect by default
        self.app.handle_message({"type": "saveSettings", "changes": {"dictation_language": "en"}}, self.bridge())
        self.assertEqual(self.app.core.language(), "en")
        self.app.handle_message({"type": "saveSettings", "changes": {"dictation_language": "fr"}}, self.bridge())
        self.assertEqual(self.app.core.language(), "en")             # unknown values are ignored

if __name__ == "__main__":
    unittest.main()
