"""Soundtrack for the film-style intro (scenes-film.html). Quiet and cinematic: a held low pad and a slow
clock-like pulse under the typing (the problem), a warm bloom when the Kalam icon appears, then a soft
76 BPM pulse with felt-piano notes, shutter ticks on the person swaps and a final chord on the end card.
Keystrokes, the icon, the key press, the swaps and the end card follow the page's cues. Pure numpy.

    python3 music_film.py cues.json out.wav
"""
import json
import sys
import wave
import numpy as np

SR = 48000
CUE = json.load(open(sys.argv[1]))
DUR = float(CUE["duration"])
ICON = float(CUE["icon"])
PRESS = float(CUE["press"])
RELEASE = float(CUE["release"])
END = float(CUE["end"])
CUTS = [float(c) for c in CUE["cuts"]]
BEAT = 60 / 76

rng = np.random.default_rng(11)
N = int(DUR * SR)
L = np.zeros(N)
R = np.zeros(N)


def add(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N or i + len(sig) <= 0:
        return
    if i < 0:
        sig, i = sig[-i:], 0
    sig = sig[: N - i]
    gl, gr = gain * np.sqrt((1 - pan) / 2) * 1.414, gain * np.sqrt((1 + pan) / 2) * 1.414
    L[i:i + len(sig)] += sig * gl
    R[i:i + len(sig)] += sig * gr


def tt(d):
    return np.arange(int(d * SR)) / SR


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def bandpass(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def noise(d):
    return rng.standard_normal(int(d * SR))


# ── Instruments ──────────────────────────────────────────────────────────────
def pad(ms, d, att=1.5, rel=1.5, bright=3):
    t = tt(d)
    s = np.zeros(len(t))
    for m in ms:
        for det in (-0.08, 0.0, 0.08):
            s += sum(np.sin(2 * np.pi * hz(m + det) * k * t + rng.uniform(0, 6)) / k ** 2 for k in range(1, bright + 1))
    return s * np.minimum(1, t / att) * np.minimum(1, np.maximum(0, d - t) / rel) / (len(ms) * 3)


def piano(m, d=2.4):
    """Soft felt-piano note: a few decaying partials with a muted attack."""
    t = tt(d)
    f = hz(m)
    s = sum(np.sin(2 * np.pi * f * k * t * (1 + 0.0004 * k * k)) / k ** 1.8 * np.exp(-t * (1.6 + 1.3 * k)) for k in range(1, 6))
    return s * np.minimum(1, t * 120)


def bell(m, d=2.0):
    t = tt(d)
    f = hz(m)
    return (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6)) * np.exp(-t * 2.2)


def sub(m, d):
    t = tt(d)
    return np.sin(2 * np.pi * hz(m) * t) * np.minimum(1, t * 30) * np.exp(-t * 2.2)


def tick():
    t = tt(0.05)
    return bandpass(noise(0.05), 2500, 8000) * np.exp(-t * 120) * 0.3


def soft_kick():
    t = tt(0.4)
    f = 45 + 45 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8)


def key_click():
    """One laptop keystroke: short bright tap with a little body."""
    d = 0.045
    t = tt(d)
    v = rng.uniform(0.75, 1.0)
    return (bandpass(noise(d), 1800, 7500) * np.exp(-t * 160) + np.sin(2 * np.pi * rng.uniform(320, 420) * t) * np.exp(-t * 90) * 0.3) * v


def shutter():
    """Freeze-cut: a soft mechanical shutter."""
    a = np.pad(bandpass(noise(0.03), 1500, 9000) * np.exp(-tt(0.03) * 150), (0, int(0.05 * SR)))
    b = bandpass(noise(0.05), 1200, 7000) * np.exp(-tt(0.05) * 110) * 0.7
    out = np.zeros(int(0.12 * SR))
    out[: len(a)] += a
    out[int(0.045 * SR):int(0.045 * SR) + len(b)] += b
    return out * 0.6


def swell(d):
    t = tt(d)
    return bandpass(noise(d), 1200, 8000) * (t / d) ** 2 * np.minimum(1, (d - t) * 20) * 0.3


def air(d=0.9):
    t = tt(d)
    return bandpass(noise(d), 500, 3500) * np.sin(np.pi * t / d) ** 2 * 0.2


def shimmer(d=2.5):
    """Bright rising sparkle for the icon."""
    s = np.zeros(int(d * SR))
    for k, m in enumerate((84, 88, 91, 96, 100)):
        b = bell(m, d - k * 0.07) * 0.12
        i = int(k * 0.07 * SR)
        s[i:i + len(b)] += b
    return s


# ── Act 1: the problem (typing). A low, unresolved pad and a slow tick. ─────
add(pad([45, 52, 57, 60], ICON + 1.2, att=2.0, rel=1.4, bright=2), 0, 0.30)
add(sub(33, ICON + 0.5), 0, 0.10)
for i, t0 in enumerate(np.arange(0.5, ICON - 0.3, BEAT * 2)):
    add(tick(), t0, 0.35, pan=0.3 if i % 2 else -0.3)
for m, t0 in ((69, 1.2), (67, 4.0), (64, 6.6), (62, 8.6)):
    add(piano(m, 3.0), t0, 0.08, pan=-0.2)
# Keystrokes from the page.
for t in CUE["keys"]:
    add(key_click(), t, 0.55, pan=0.25)

# ── Act 2: Kalam. Warm bloom, then a gentle pulse. ──────────────────────────
add(swell(1.6), ICON - 1.6, 0.6)
add(shimmer(), ICON, 0.9, pan=0.15)
CHORDS = [(41, [65, 69, 72, 76]), (36, [64, 67, 72, 74]), (38, [62, 65, 69, 72]), (34, [62, 65, 70, 74])]  # Fmaj7 C(add9) Dm7 Bbmaj7
BAR = 4 * BEAT
t0, b = ICON, 0
while t0 < END - 0.5:
    root, tones = CHORDS[b % 4]
    add(pad(tones, BAR + 1.0, att=0.8, rel=1.0), t0, 0.26)
    add(sub(root, BAR), t0, 0.16)
    # Felt-piano arpeggio, sparser at first.
    steps = [0, 2] if t0 < PRESS else [0, 1.5, 2, 3]
    for k, s in enumerate(steps):
        add(piano(tones[(k * 2 + b) % 4] + 12, 2.6), t0 + s * BEAT, 0.07, pan=0.25 * (-1) ** k)
    # Soft heartbeat pulse once he starts talking.
    if t0 >= PRESS - BAR:
        for beat in range(4):
            if beat in (0, 2):
                add(soft_kick(), t0 + beat * BEAT, 0.32)
            add(tick(), t0 + beat * BEAT + BEAT / 2, 0.2, pan=0.35)
    t0 += BAR
    b += 1

# Key press and release.
add(np.sin(2 * np.pi * 170 * tt(0.25)) * np.exp(-tt(0.25) * 30) * 0.5, PRESS, 0.7)
add(key_click(), PRESS, 0.9)
add(key_click(), RELEASE, 0.7)
for m, k in ((84, 0), (91, 1)):
    add(bell(m, 1.4), CUE["chime"][0] + k * 0.08, 0.06)
for m, k in ((86, 0), (93, 1)):
    add(bell(m, 1.4), CUE["chime"][1] + k * 0.08, 0.05)

# Scene changes and swaps.
for c in CUTS:
    add(air(), c - 0.45, 0.35)
for s in CUE["swaps"]:
    add(shutter(), s - 0.01, 0.8, pan=0.1)

# ── End card ────────────────────────────────────────────────────────────────
add(swell(1.2), END - 1.2, 0.5)
add(pad([53, 60, 65, 69, 72, 76], DUR - END + 0.5, att=0.4, rel=3.5), END - 0.1, 0.32)
add(sub(29, 4.0), END, 0.14)
for k, m in enumerate([77, 81, 84, 88]):
    add(bell(m, 3.0), END + k * 0.14, 0.08, pan=-0.3 + 0.2 * k)

# ── Master ───────────────────────────────────────────────────────────────────
mix = np.stack([L, R])
fade = np.ones(N)
fade[: int(0.3 * SR)] = np.linspace(0, 1, int(0.3 * SR))
fo = int(3.0 * SR)
fade[-fo:] = np.linspace(1, 0, fo) ** 1.5
mix *= fade
mix /= np.max(np.abs(mix)) + 1e-9
mix = np.tanh(mix * 1.2) / np.tanh(1.2)
mix *= 10 ** (-1.0 / 20)
pcm = (mix.T * 32767).astype("<i2")

with wave.open(sys.argv[2], "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", sys.argv[2], f"{DUR:.1f}s")
