"""
Arabic clean-up for dictation. Pure Python, so it can be tested anywhere.

Whisper's Arabic output needs a few fixes before it's typed:
  - diacritics (harakat) and tatweel appear at random; typed Arabic rarely uses them
  - digits come out as Arabic-Indic (١٢٣) or Western (123) inconsistently; we use Western
  - Latin punctuation (? , ;) appears inside Arabic sentences instead of ؟ ، ؛
  - hesitation sounds and self-corrections need Arabic equivalents of the English lists

Kept deliberately conservative: words that are hesitations in one dialect but real
words in another (آه = "yes" in Egyptian, يعني = "means") are left alone.
"""

import re

_ARABIC = re.compile(r"[؀-ۿݐ-ݿ]")
_LATIN = re.compile(r"[A-Za-z]")

# Harakat (fatha, damma, kasra, tanween, shadda, sukun), superscript alef, tatweel.
_MARKS = re.compile(r"[ً-ْٰـ]")

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "0123456789" * 2)

# Pure hesitation sounds only (as whole words).
FILLERS = ["اممم", "امم", "ممم", "مم", "إمم", "أمم", "ااا", "آآآ", "آآ", "ءء", "ههه"]

# Self-corrections, mirroring the English "scratch that" / "no wait" lists.
# Hard: drop the sentence said before. Soft: replace the last few words.
BACKTRACK_HARD = ["امسح هذا", "امسح هذي", "امسح هذه", "امسح ذلك", "امسحها", "احذف هذا",
                  "احذف هذي", "احذف هذه", "الغي هذا", "ألغي هذا", "انس هذا", "انسى هذا"]
BACKTRACK_SOFT = ["لا لا أقصد", "لا أقصد", "لا اقصد", "قصدي", "لا لحظة", "لا عفوا", "لا عفواً"]

SENTENCE_END = ".!?؟"
CLAUSE_MARKS = ",;!?،؛؟"


def is_mostly_arabic(text):
    arabic = len(_ARABIC.findall(text))
    return arabic > 0 and arabic >= len(_LATIN.findall(text))


def remove_fillers(text):
    for word in sorted(FILLERS, key=len, reverse=True):
        text = re.sub(rf"(?<!\w){re.escape(word)}(?!\w)[،,]?\s*", "", text)
    return text


def normalize(text, western_digits=True):
    """Clean Arabic text for typing. English text passes through unchanged
    (apart from Arabic-Indic digits, which become Western)."""
    text = _MARKS.sub("", text)
    if western_digits:
        text = text.translate(_DIGITS)
    if is_mostly_arabic(text):
        # Latin punctuation inside Arabic → Arabic forms (not inside numbers like 3,500 or 4.5).
        text = re.sub(r"\?", "؟", text)
        text = re.sub(r"(?<!\d),|,(?!\d)", "،", text)
        text = text.replace(";", "؛")
    text = re.sub(r"\s+([.,!?;:،؛؟])", r"\1", text)          # no space before punctuation
    text = re.sub(r"([،؛])(?=\S)", r"\1 ", text)              # one space after Arabic comma/semicolon
    return re.sub(r"\s{2,}", " ", text).strip()
