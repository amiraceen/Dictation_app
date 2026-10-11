"""Tests for the platform-independent parts: settings, notes, meetings, system helpers, notetaker.

Run: python3 -m unittest discover -s tests
"""

import os
import sys
import tempfile
import threading
import time
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import meetings
import notes
import notetaker
import settings
import system


class SettingsTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "settings.json")

    def test_defaults_and_persist(self):
        s = settings.Settings(self.path)
        self.assertEqual(s["max_recording_minutes"], 120)
        self.assertEqual(s.update({"sounds": False, "max_recording_minutes": 60.0}),
                         ["sounds", "max_recording_minutes"])
        again = settings.Settings(self.path)
        self.assertFalse(again["sounds"])
        self.assertEqual(again["max_recording_minutes"], 60)
        self.assertIs(type(again["max_recording_minutes"]), int)

    def test_rejects_invalid(self):
        s = settings.Settings(self.path)
        self.assertEqual(s.update({"sounds": "yes", "max_recording_minutes": 7, "nope": 1,
                                   "notify_before_meeting": True}), [])
        self.assertEqual(s.update({"meeting_shortcut": {"keycode": 46, "mods": [], "label": "M"}}), [])
        self.assertFalse(os.path.exists(self.path))

    def test_corrupt_file_falls_back(self):
        with open(self.path, "w") as f:
            f.write("{not json")
        self.assertTrue(settings.Settings(self.path)["sounds"])

    def test_shortcut_update(self):
        s = settings.Settings(self.path)
        sc = system.shortcut_from_js("KeyN", ["cmd", "shift"])
        self.assertEqual(s.update({"meeting_shortcut": sc}), ["meeting_shortcut"])
        self.assertEqual(settings.Settings(self.path)["meeting_shortcut"]["label"], "⇧⌘ N")


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


class MeetingsTest(unittest.TestCase):

    def ev(self, start, end=None, title="Sync", all_day=False, id_="1"):
        return {"id": id_, "title": title, "start": start, "end": end or start + 1800, "all_day": all_day}

    def test_countdown(self):
        self.assertEqual(meetings.format_countdown(-5), "now")
        self.assertEqual(meetings.format_countdown(45), "in 45s")
        self.assertEqual(meetings.format_countdown(61), "in 2m")
        self.assertEqual(meetings.format_countdown(3600), "in 1h")
        self.assertEqual(meetings.format_countdown(3900), "in 1h 5m")

    def test_next_meeting(self):
        now = 10_000
        evs = [self.ev(now - 3000, now + 600, id_="long-running"),     # started 50 min ago
               self.ev(now + 900, id_="later"), self.ev(now + 300, id_="soon"),
               self.ev(now + 100, all_day=True, id_="allday"),
               self.ev(now + 13 * 3600, id_="tomorrow")]
        self.assertEqual(meetings.next_meeting(evs, now)["id"], "soon")
        self.assertEqual(meetings.next_meeting([self.ev(now - 120, id_="now")], now)["id"], "now")
        self.assertIsNone(meetings.next_meeting(evs[3:], now))
        self.assertEqual(meetings.menubar_text(self.ev(now + 300, title="A very long meeting title indeed"), now),
                         "A very long meeting t… · in 5m")

    def test_notifier_fires_once(self):
        n = meetings.MeetingNotifier()
        e = self.ev(1000)
        self.assertEqual(n.due([e], 980, 15), [])
        self.assertEqual(n.due([e], 985, 15), [e])
        self.assertEqual(n.due([e], 990, 15), [])
        self.assertEqual(n.due([self.ev(1000, id_="2")], 1100, 15), [])    # too late
        self.assertEqual(n.due([self.ev(2000, id_="3")], 1999, -1), [])    # off

    def test_call_tracker_debounce(self):
        t = meetings.CallTracker()
        self.assertIsNone(t.update(True, 0, "zoom.us"))
        self.assertIsNone(t.update(False, 1))           # blip
        self.assertIsNone(t.update(True, 2, "zoom.us"))
        self.assertEqual(t.update(True, 5.5, "zoom.us"), "started")
        self.assertEqual(t.app, "zoom.us")
        self.assertIsNone(t.update(False, 10))
        self.assertIsNone(t.update(True, 20))            # mute/unmute doesn't end it
        self.assertIsNone(t.update(False, 30))
        self.assertEqual(t.update(False, 45), "ended")


class SystemTest(unittest.TestCase):

    def test_shortcuts(self):
        sc = system.shortcut_from_js("KeyM", ["alt"])
        self.assertEqual(sc, settings.DEFAULT_SHORTCUT)
        self.assertIsNone(system.shortcut_from_js("KeyM", ["shift"]))
        self.assertIsNone(system.shortcut_from_js("Enter", ["cmd"]))
        self.assertEqual(system.shortcut_from_js("Digit5", ["ctrl", "alt"])["label"], "⌃⌥ 5")
        alt = system.FLAG_MASKS["alt"]
        self.assertTrue(system.shortcut_matches(sc, 46, alt | 0x100))       # device-specific bits ignored
        self.assertFalse(system.shortcut_matches(sc, 46, alt | system.FLAG_MASKS["shift"]))
        self.assertFalse(system.shortcut_matches(sc, 45, alt))

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

    def test_split_frames(self):
        # 1440x900 primary screen, menu bar 25 px, Dock 70 px at the bottom.
        left, right = system.split_frames((0, 70, 1440, 805), 900)
        self.assertEqual(left, (0, 25, 720, 805))
        self.assertEqual(right, (720, 25, 720, 805))


def tone(secs, amp=0.1, sr=16000):
    t = np.arange(int(secs * sr)) / sr
    return (amp * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


class ChunkerTest(unittest.TestCase):

    def test_cuts_at_pause(self):
        c = notetaker.Chunker()
        audio = np.concatenate([tone(7), np.zeros(16000, np.float32), tone(3)])
        chunks = []
        for i in range(0, len(audio), 1024):
            chunks += c.feed(audio[i:i + 1024])
        self.assertEqual(len(chunks), 1)
        start, a = chunks[0]
        self.assertEqual(start, 0)
        self.assertTrue(7.5 <= len(a) / 16000 <= 8.0)
        rest = c.flush()
        self.assertAlmostEqual(rest[0], len(a) / 16000)
        self.assertEqual(len(a) + len(rest[1]), len(audio))

    def test_forced_cut_without_pause(self):
        c = notetaker.Chunker()
        audio = tone(45)
        audio[int(12 * 16000):int(12.1 * 16000)] *= 0.2      # quietest moment ~12 s
        chunks = []
        for i in range(0, len(audio), 1024):
            chunks += c.feed(audio[i:i + 1024])
        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(11.9 <= len(chunks[0][1]) / 16000 <= 12.2)
        total = sum(len(a) for _, a in chunks) + len(c.flush()[1])
        self.assertEqual(total, len(audio))

    def test_silence_detection(self):
        c = notetaker.Chunker()
        self.assertTrue(c.is_silent(np.zeros(16000, np.float32)))
        self.assertFalse(c.is_silent(tone(1)))


class MixerTest(unittest.TestCase):

    def test_mix_pads_and_drops_backlog(self):
        m = notetaker.Mixer(max_lag=0.1)
        m.push_system(np.full(500, 0.5, np.float32))
        out = m.mix(np.full(1000, 0.1, np.float32))
        self.assertAlmostEqual(float(out[0]), 0.6, places=5)
        self.assertAlmostEqual(float(out[-1]), 0.1, places=5)
        m.push_system(np.ones(5000, np.float32))           # > 0.1 s backlog: keep newest 1600
        self.assertEqual(len(m._sys), 1600)
        self.assertEqual(float(m.mix(np.full(10, 0.9, np.float32)).max()), 1.0)   # clipped


class FakeStream:
    """Plays a fixed signal at real-time-ish speed."""

    def __init__(self, audio):
        self.audio, self.pos = audio, 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n):
        time.sleep(0.001)
        block = self.audio[self.pos:self.pos + n]
        self.pos += n
        if len(block) < n:
            block = np.concatenate([block, np.zeros(n - len(block), np.float32)])
        return block.reshape(-1, 1), False


class NotetakerTest(unittest.TestCase):

    def run_notetaker(self, audio, max_secs=3600, stop_after=None, system_audio=None):
        segments, stopped, warnings = [], threading.Event(), []
        result = {}
        n = notetaker.Notetaker(
            transcribe=lambda a: f"{len(a) / 16000:.1f}s",
            on_segment=lambda nid, start, text: segments.append((nid, start, text)),
            on_stopped=lambda nid, dur, reason: (result.update(nid=nid, reason=reason), stopped.set()),
            on_warning=lambda nid, left: warnings.append(left),
            input_stream=lambda: FakeStream(audio),
            system_audio=system_audio)
        self.assertTrue(n.start("note1", max_secs))
        self.assertFalse(n.start("note2", max_secs))         # one at a time
        if stop_after is not None:
            time.sleep(stop_after)
            n.stop()
        self.assertTrue(stopped.wait(10))
        self.assertFalse(n.active)
        return segments, result, warnings

    def test_records_chunks_and_flushes_on_stop(self):
        audio = np.concatenate([tone(7), np.zeros(16000, np.float32), tone(2)])
        segs, result, _ = self.run_notetaker(audio, stop_after=0.4)
        self.assertEqual(result, {"nid": "note1", "reason": "user"})
        self.assertGreaterEqual(len(segs), 2)
        self.assertEqual(segs[0][1], 0)

    def test_max_length_stops_with_warning(self):
        segs, result, warnings = self.run_notetaker(tone(60), max_secs=0.2)
        self.assertEqual(result["reason"], "max_length")
        self.assertEqual(len(warnings), 1)

    def test_system_audio_failure_falls_back_to_mic(self):
        class Broken:
            def __init__(self, push, err):
                pass

            def start(self):
                raise RuntimeError("no permission")

        segs, result, _ = self.run_notetaker(tone(3), stop_after=0.2, system_audio=Broken)
        self.assertEqual(result["reason"], "user")
        self.assertTrue(segs)


if __name__ == "__main__":
    unittest.main()
