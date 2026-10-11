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

LANGUAGE_OPTIONS = [("auto", "Auto-detect"), ("en", "English"), ("ar", "Arabic")]


def whisper_language(setting):
    """Settings value → Whisper's language argument (None = detect every time)."""
    return None if setting == "auto" else setting
