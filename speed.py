"""Speed settings for Whisper. Pure Python, so it can be tested anywhere."""

import os
import subprocess

# Timestamps aren't used and previous-text conditioning only matters past 30 s,
# so both are off in every mode; that doesn't change the words.
# ACCURATE keeps beam search (5 candidates). FAST is greedy (the single most likely
# word at each step): quicker, but more slips on names and mixed languages.
ACCURATE_DECODE = dict(beam_size=5, without_timestamps=True, condition_on_previous_text=False)
FAST_DECODE = dict(beam_size=1, without_timestamps=True, condition_on_previous_text=False)


def decode_options(fast):
    return FAST_DECODE if fast else ACCURATE_DECODE


def cpu_threads():
    """Threads for the model: the Mac's performance cores (efficiency cores slow it down)."""
    try:
        out = subprocess.run(["sysctl", "-n", "hw.perflevel0.physicalcpu"],
                             capture_output=True, text=True, timeout=2).stdout.strip()
        if out.isdigit() and int(out) > 0:
            return min(int(out), 8)
    except (OSError, subprocess.SubprocessError):
        pass
    return max(1, min(os.cpu_count() or 4, 8))
