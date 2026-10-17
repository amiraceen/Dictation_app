"""Tests for the platform-independent parts: settings, notes and system helpers.

Run: python3 -m unittest discover -s tests
"""

import os
import sys
import tempfile
import unittest


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import notes
import settings
import system


class SettingsTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "settings.json")

    def test_defaults_and_persist(self):
        s = settings.Settings(self.path)
        self.assertEqual(s["dictation_language"], "auto")
        self.assertEqual(s.update({"sounds": False, "dictation_language": "ar"}), ["sounds", "dictation_language"])
        again = settings.Settings(self.path)
        self.assertFalse(again["sounds"])
        self.assertEqual(again["dictation_language"], "ar")

    def test_rejects_invalid(self):
        s = settings.Settings(self.path)
        self.assertEqual(s.update({"sounds": "yes", "dictation_language": "xx", "nope": 1,
                                   "meeting_shortcut": {"keycode": 46}}), [])
        self.assertFalse(os.path.exists(self.path))

    def test_corrupt_file_falls_back(self):
        with open(self.path, "w") as f:
            f.write("{not json")
        self.assertTrue(settings.Settings(self.path)["sounds"])


class NotesTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = notes.NotesStore(self.dir)

    def test_lifecycle(self):
        n = self.store.create("Standup", meeting=True, now=1000)
        self.store.update(n["id"], body="Ship Friday")
        self.store.append_transcript(n["id"], 0, "Hello everyone.")
        self.store.append_transcript(n["id"], 65.24, "  Next item.  ")
        self.store.append_transcript(n["id"], 70, "   ")
        self.store.set_recording(n["id"], False, duration=3725.04)
        reloaded = notes.NotesStore(self.dir).get(n["id"])
        self.assertEqual(reloaded["body"], "Ship Friday")
        self.assertEqual([s["text"] for s in reloaded["transcript"]], ["Hello everyone.", "Next item."])
        self.assertEqual(reloaded["duration"], 3725.0)
        md = self.store.to_markdown(n["id"])
        self.assertIn("# Standup", md)
        self.assertIn("[1:05] Next item.", md)
        self.assertTrue(self.store.delete(n["id"]))
        self.assertEqual(os.listdir(self.dir), [])

    def test_summaries_newest_first_and_preview(self):
        a = self.store.create("A", now=1)
        self.store.create("B", now=2)
        self.store.append_transcript(a["id"], 0, "from transcript")
        s = self.store.summaries()
        self.assertEqual([x["title"] for x in s], ["B", "A"])
        self.assertEqual(s[1]["preview"], "from transcript")
        self.assertNotIn("transcript", s[0])

    def test_recover_interrupted_and_bad_id(self):
        n = self.store.create()
        self.store.set_recording(n["id"], True)
        store2 = notes.NotesStore(self.dir)
        store2.recover_interrupted()
        self.assertFalse(store2.get(n["id"])["recording"])
        self.assertFalse(self.store.update("../../etc/passwd", body="x"))
        self.assertEqual(os.path.dirname(self.store._path("../x")), self.dir)


class SystemTest(unittest.TestCase):

    def test_dictation_key_labels(self):
        self.assertEqual(system.key_label(61), "Right ⌥")
        self.assertEqual(system.key_label(61, "ar"), "⌥ اليمين")
        self.assertEqual(system.key_label(54), "Right ⌘")
        self.assertEqual(system.key_label(63), "Fn 🌐")
        self.assertEqual(system.key_label(96), "F5")
        self.assertEqual(system.key_label(46), "M")
        self.assertEqual(system.keycode_from_js("AltRight"), 61)
        self.assertEqual(system.keycode_from_js("F5"), 96)
        self.assertIsNone(system.keycode_from_js("Escape"))
        self.assertTrue(system.is_modifier(61) and not system.is_modifier(96))

    def test_dictation_key_setting(self):
        path = os.path.join(tempfile.mkdtemp(), "s.json")
        s = settings.Settings(path)
        self.assertEqual(s["dictation_key"], 61)
        self.assertEqual(s.update({"dictation_key": 96.0}), ["dictation_key"])     # JS numbers arrive as floats
        self.assertEqual(settings.Settings(path)["dictation_key"], 96)
        self.assertEqual(s.update({"dictation_key": 999}), [])                    # not a real key
        self.assertEqual(s.update({"dictation_key": True}), [])

    def test_login_agent(self):
        exe = "/Applications/Dictation.app/Contents/MacOS/Dictation"
        self.assertEqual(system.login_program_args(True, exe, "x.py"),
                         ["/usr/bin/open", "-a", "/Applications/Dictation.app"])
        self.assertEqual(system.login_program_args(False, "/venv/bin/python", "/src/dictation.py"),
                         ["/venv/bin/python", "/src/dictation.py"])
        self.assertTrue(system.login_agent_plist(["a"])["RunAtLoad"])

    def test_media_scripts(self):
        self.assertIn('application "Spotify" is running', system.pause_media_script())
        self.assertEqual(system.parse_paused("Music, Spotify\n"), ["Music", "Spotify"])
        self.assertEqual(system.parse_paused(""), [])
        self.assertNotIn("Evil", system.resume_media_script(["Music", "Evil"]))


if __name__ == "__main__":
    unittest.main()
