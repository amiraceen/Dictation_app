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


if __name__ == "__main__":
    unittest.main()
