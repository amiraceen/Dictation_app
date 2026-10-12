"""Arabic clean-up. Run: python3 -m unittest discover -s tests"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import arabic  # noqa: E402


class ArabicNormalizeTest(unittest.TestCase):

    def test_diacritics_tatweel_digits(self):
        self.assertEqual(arabic.normalize("مَرْحَباً بِكُمْ في الاجتمـــاع رقم ٣"), "مرحبا بكم في الاجتماع رقم 3")

    def test_latin_punctuation_becomes_arabic(self):
        self.assertEqual(arabic.normalize("هل ترون الشاشة ? نعم , واضحة ; شكرا"), "هل ترون الشاشة؟ نعم، واضحة؛ شكرا")
        self.assertEqual(arabic.normalize("السعر 3,500 ريال"), "السعر 3,500 ريال")     # numbers untouched
        self.assertEqual(arabic.normalize("الساعة 4.30"), "الساعة 4.30")

    def test_english_unchanged(self):
        self.assertEqual(arabic.normalize("Hi team, can we meet at 3.30?"), "Hi team, can we meet at 3.30?")

    def test_mixed_mostly_arabic(self):
        self.assertEqual(arabic.normalize("أرسل الملف على Slack , لو سمحت ?"), "أرسل الملف على Slack، لو سمحت؟")

    def test_fillers(self):
        self.assertEqual(arabic.remove_fillers("اممم أبي أحجز موعد"), "أبي أحجز موعد")
        self.assertEqual(arabic.remove_fillers("آه تمام"), "آه تمام")                   # Egyptian "yes" stays
        self.assertEqual(arabic.remove_fillers("الممثل"), "الممثل")                     # not inside words


class LanguagePickTest(unittest.TestCase):
    """Auto-detect only ever picks Arabic or English, leaning Arabic."""

    def test_pick(self):
        import speed
        self.assertEqual(speed.pick_language([("he", 0.45), ("ar", 0.2), ("en", 0.2)]), "ar")   # was Hebrew
        self.assertEqual(speed.pick_language([("en", 0.5), ("ar", 0.3)]), "ar")                # was English
        self.assertEqual(speed.pick_language([("en", 0.9), ("ar", 0.04)]), "en")
        self.assertEqual(speed.pick_language([("fr", 0.9), ("en", 0.05)]), "en")

    def test_prompt(self):
        self.assertIn("شحالش", arabic.initial_prompt("ar"))
        self.assertTrue(arabic.initial_prompt("ar", ["مسقط"]).endswith("مسقط"))
        self.assertEqual(arabic.initial_prompt("en", ["Maal", "Kalam"]), "Maal, Kalam")
        self.assertIsNone(arabic.initial_prompt("en"))
        self.assertIsNone(arabic.initial_prompt("ar", dialect=False))


class ModelStoreTest(unittest.TestCase):

    def test_download_then_ready(self):
        import tempfile
        import threading
        import models
        calls, gate = [], threading.Event()

        def fake(name, folder):
            calls.append(name)
            gate.wait(2)
            with open(os.path.join(folder, "model.bin"), "wb") as f:
                f.write(b"x" * 1000)

        store = models.ModelStore(tempfile.mkdtemp(), builtin_path="/app/model", downloader=fake)
        self.assertTrue(store.ready("small"))
        self.assertEqual(store.path("small"), "/app/model")
        self.assertFalse(store.ready("turbo"))
        done = []
        store.download("turbo", done.append)
        self.assertEqual(store.downloading, "turbo")
        self.assertIsNotNone(store.progress())
        store.download("turbo", done.append)            # second click while running: ignored
        gate.set()
        store._thread.join(2)
        self.assertEqual((calls, done), (["turbo"], [True]))
        self.assertTrue(store.ready("turbo"))
        self.assertIsNone(store.progress())
        self.assertTrue(store.path("turbo").endswith("whisper-large-v3-turbo-mlx"))
        self.assertEqual(store.engine("turbo"), "mlx")

    def test_removes_old_cpu_turbo_download(self):
        import tempfile
        import models
        folder = tempfile.mkdtemp()
        os.makedirs(os.path.join(folder, "large-v3-turbo"))
        models.ModelStore(folder)
        self.assertFalse(os.path.exists(os.path.join(folder, "large-v3-turbo")))

    def test_failed_download_reports_error(self):
        import tempfile
        import models

        def fail(name, folder):
            raise OSError("no internet")

        store = models.ModelStore(tempfile.mkdtemp(), downloader=fail)
        done = []
        store.download("turbo", done.append)
        store._thread.join(2)
        self.assertEqual(done, [False])
        self.assertEqual(store.error, "no internet")
        self.assertFalse(store.ready("turbo"))


if __name__ == "__main__":
    unittest.main()
