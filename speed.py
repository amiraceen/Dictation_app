"""Speed settings for Whisper. Pure Python, so it can be tested anywhere.

Measured on a GitHub-hosted Apple-silicon Mac (5 s clip, tools/bench_latency.py):
automatic language detection roughly doubles the time, because the audio is
processed once to detect the language and again to transcribe it. Greedy
decoding and pinned thread counts made no measurable difference, so beam
search (the more accurate decoder) stays.
"""

# Timestamps aren't used and previous-text conditioning only matters past 30 s;
# turning them off doesn't change the words.
DECODE = dict(beam_size=5, without_timestamps=True, condition_on_previous_text=False)

LANGUAGE_OPTIONS = [("auto", "Auto-detect"), ("en", "English"), ("ar", "Arabic")]


def whisper_language(setting):
    """Settings value → Whisper's language argument (None = detect every time)."""
    return None if setting == "auto" else setting
