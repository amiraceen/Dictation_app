"""Speed settings for Whisper. Pure Python, so it can be tested anywhere.

Measured on a GitHub-hosted Apple-silicon Mac (5 s clip, tools/bench_latency.py):
automatic language detection roughly doubles the time, because the audio is
processed once to detect the language and again to transcribe it. Greedy
decoding, pinned thread counts and turning timestamps off made no measurable
difference (and the last two changed the text), so the defaults stay.
"""

# Whisper's defaults. Turning timestamps off was tried: no measurable speed-up,
# and it changed the text ("3.30" became "330"), so the defaults stay.
DECODE = dict(beam_size=5)

LANGUAGE_OPTIONS = [("auto", "Arabic or English (auto)"), ("ar", "Arabic"), ("en", "English")]

# Whisper often hears short Gulf, Omani or Egyptian clips as one of these and then writes
# Hebrew, Persian or Urdu. When detecting, they all count as Arabic.
ARABIC_LOOKALIKES = {"ar", "he", "fa", "ur", "ps", "sd", "ug", "yi", "mt"}
ARABIC_WEIGHT = 2.0      # most users speak Arabic: English must be twice as likely to win


def whisper_language(setting):
    """Settings value → Whisper's language argument (None = detect Arabic or English)."""
    return None if setting == "auto" else setting


def pick_language(probs):
    """Choose "ar" or "en" from Whisper's language probabilities [(code, p), ...].

    Free detection over 100 languages turned "بغيت اقولش" into Hebrew and
    "كيفكن يا بنات" into English; only Arabic and English are ever chosen here."""
    arabic = sum(p for code, p in probs if code in ARABIC_LOOKALIKES)
    english = sum(p for code, p in probs if code == "en")
    return "ar" if arabic * ARABIC_WEIGHT >= english else "en"
