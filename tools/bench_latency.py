"""Time how long transcription takes after the key is released, for different settings.

    python tools/bench_latency.py clip.wav [model_dir_or_size]

Prints the median of several runs per configuration (after one warm-up run).
"""

import statistics
import sys
import time
import wave

import numpy as np
from faster_whisper import WhisperModel

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
from speed import cpu_threads  # noqa: E402

RUNS = 5


def load(path):
    w = wave.open(path)
    assert w.getframerate() == 16000 and w.getnchannels() == 1, "need 16 kHz mono WAV"
    return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


def run(model, audio, **kw):
    segs, _ = model.transcribe(audio, vad_filter=True, vad_parameters=dict(min_silence_duration_ms=300), **kw)
    return " ".join(s.text for s in segs).strip()


def bench(name, model, audio, **kw):
    text = run(model, audio, **kw)                 # warm-up
    times = []
    for _ in range(RUNS):
        t = time.perf_counter()
        run(model, audio, **kw)
        times.append(time.perf_counter() - t)
    print(f"{name:<44} median {statistics.median(times):.2f}s  min {min(times):.2f}s  | {text}", flush=True)
    return statistics.median(times)


if __name__ == "__main__":
    audio = load(sys.argv[1])
    model_id = sys.argv[2] if len(sys.argv) > 2 else "small"
    print(f"clip {len(audio) / 16000:.1f}s, model {model_id}, {RUNS} runs each", flush=True)
    old = WhisperModel(model_id, device="cpu", compute_type="int8")
    base = bench("before: beam 5, timestamps, default threads", old, audio)
    new = WhisperModel(model_id, device="cpu", compute_type="int8", cpu_threads=cpu_threads())
    bench(f"threads={cpu_threads()}, beam 5", new, audio)
    fast = bench(f"after: threads={cpu_threads()}, beam 1, no timestamps", new, audio,
                 beam_size=1, without_timestamps=True, condition_on_previous_text=False)
    bench("after + language fixed to English", new, audio, beam_size=1, without_timestamps=True,
          condition_on_previous_text=False, language="en")
    print(f"speed-up: {base / fast:.1f}x", flush=True)
