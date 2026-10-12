"""Voice test storage, scoring and recording. Run: python3 -m unittest discover -s tests"""

import os
import sys
import tempfile
import time
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import voicetest  # noqa: E402


class ScoringTest(unittest.TestCase):

    def test_word_errors_ignore_spelling_variants(self):
        # Diacritics, hamza forms, taa marbuta, punctuation and digits don't count as errors.
        self.assertEqual(voicetest.word_errors("أنا ذاهبٌ إلى المدرسة ٣ مرات؟", "انا ذاهب الى المدرسه 3 مرات"), (0, 6))

    def test_word_errors_counts(self):
        self.assertEqual(voicetest.word_errors("وين صرت الحين", "وين سرت"), (2, 3))     # 1 sub + 1 deletion
        self.assertEqual(voicetest.word_errors("ابعث لي الـ presentation", "ابعث لي البريزنتيشن"), (1, 3))
        self.assertAlmostEqual(voicetest.accuracy(1, 4), 0.75)
        self.assertEqual(voicetest.accuracy(9, 4), 0.0)


class StoreTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def test_defaults_record_remove_persist(self):
        s = voicetest.VoiceTestStore(self.dir)
        n = len(voicetest.DEFAULT_PHRASES)
        self.assertEqual(len(s.state()["phrases"]), n)
        self.assertTrue(s.save_recording("gulf-1", np.zeros(16000, np.float32) + 0.1))
        self.assertEqual(s.phrase("gulf-1")["secs"], 1.0)
        custom = s.add("  أبي قهوة  ")
        self.assertTrue(s.remove("egy-1"))
        s2 = voicetest.VoiceTestStore(self.dir)                  # removed defaults stay removed
        ids = [p["id"] for p in s2.state()["phrases"]]
        self.assertNotIn("egy-1", ids)
        self.assertIn(custom["id"], ids)
        self.assertEqual([p["id"] for p in s2.recorded()], ["gulf-1"])
        self.assertIsNone(s.add("   "))

    def test_results_and_export_roundtrip(self):
        s = voicetest.VoiceTestStore(self.dir)
        audio = (0.2 * np.sin(np.arange(8000) / 5)).astype(np.float32)
        s.save_recording("msa-1", audio)
        s.set_results("small", "ar", {"msa-1": {"heard": "x", "errors": 2, "words": 8, "secs": 1.2}})
        self.assertAlmostEqual(s.state()["results"]["accuracy"], 0.75)
        s.save_recording("msa-1", audio)                          # re-recording clears its old result
        self.assertNotIn("msa-1", s.state()["results"]["per"])
        z = os.path.join(self.dir, "set.zip")
        self.assertEqual(s.export_zip(z), 1)
        (pid, dialect, back, text), = voicetest.load_zip(z)
        self.assertEqual((pid, dialect), ("msa-1", "MSA"))
        self.assertLess(float(np.abs(back - audio).max()), 1e-3)
        self.assertIn("الاجتماع", text)


class FakeStream:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n):
        time.sleep(0.002)
        return np.full((n, 1), 0.1, np.float32), False


class RecorderTest(unittest.TestCase):

    def test_start_stop(self):
        r = voicetest.PhraseRecorder(input_stream=FakeStream)
        self.assertTrue(r.start("gulf-1"))
        self.assertFalse(r.start("gulf-2"))                       # one at a time
        time.sleep(0.1)
        pid, samples = r.stop()
        self.assertEqual(pid, "gulf-1")
        self.assertGreater(len(samples), 1024)
        self.assertFalse(r.active)
        self.assertEqual(r.stop(), (None, None))


if __name__ == "__main__":
    unittest.main()
