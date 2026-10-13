"""Soundtrack for the calm vertical promo (scenes-calm.html): an upbeat but soft
120 BPM groove (round kick, shaker, rim, echoing plucks, warm pad) with quiet UI
sound effects. Pure numpy, no samples.

    python3 music_calm.py out.wav
"""
import sys
import wave
import numpy as np

SR = 48000
BEAT = 0.5
BAR = 4 * BEAT
DUR = 42.0
DROP = 4.0            # groove starts when Right ⌥ is pressed
OUTRO = 37.5
END_DRUMS = 40.0
CUTS = [8.0, 14.0, 20.0, 28.0, 34.0, 37.5]

rng = np.random.default_rng(5)
N = int(DUR * SR)
L = np.zeros(N)
R = np.zeros(N)


def add(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N or i + len(sig) <= 0:
        return
    sig = sig[: N - i]
    gl, gr = gain * np.sqrt((1 - pan) / 2) * 1.414, gain * np.sqrt((1 + pan) / 2) * 1.414
    L[i:i + len(sig)] += sig * gl
    R[i:i + len(sig)] += sig * gr


def echo(sig, t, gain, pan, taps=3, gap=0.375, fb=0.45):
    """Ping-pong echo: the plucks ring out softly left and right."""
    for k in range(taps + 1):
        add(sig, t + k * gap, gain * fb ** k, pan * (-1) ** k)


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
def kick():
    t = tt(0.35)
    f = 50 + 70 * np.exp(-t * 34)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def rim():
    t = tt(0.06)
    return (np.sin(2 * np.pi * 1700 * t) * 0.5 + bandpass(noise(0.06), 2000, 6000) * 0.5) * np.exp(-t * 70)


def shaker():
    t = tt(0.07)
    return bandpass(noise(0.07), 5000, 12000) * np.sin(np.pi * t / t[-1]) ** 2 * 0.25


def pluck(m, d=0.6):
    t = tt(d)
    f = hz(m)
    s = sum(np.sin(2 * np.pi * f * k * t) / k ** 1.6 * np.exp(-t * (4 + 4 * k)) for k in range(1, 5))
    return s * np.minimum(1, t * 300)


def bass(m, d):
    t = tt(d)
    s = np.sin(2 * np.pi * hz(m) * t) + 0.25 * np.sin(4 * np.pi * hz(m) * t)
    return s * np.minimum(1, t * 200) * np.exp(-t * 1.6) * np.minimum(1, (d - t) * 40)


def pad(ms, d):
    t = tt(d)
    s = np.zeros(len(t))
    for m in ms:
        for det in (-0.1, 0.0, 0.1):
            s += sum(np.sin(2 * np.pi * hz(m + det) * k * t + rng.uniform(0, 6)) / k ** 2 for k in range(1, 4))
    return s * np.minimum(1, t / 0.6) * np.minimum(1, (d - t) / 0.6) / (len(ms) * 3)


def bell(m, d=1.4):
    t = tt(d)
    f = hz(m)
    return (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6)) * np.exp(-t * 2.6)


def swell(d):
    """Airy rising breath used instead of risers and crashes."""
    t = tt(d)
    return bandpass(noise(d), 1500, 9000) * (t / d) ** 2 * np.minimum(1, (d - t) * 20) * 0.35


# ── SFX ──────────────────────────────────────────────────────────────────────
def click(g=0.4):
    t = tt(0.03)
    return bandpass(noise(0.03), 2000, 7000) * np.exp(-t * 200) * g


def soft_thud():
    t = tt(0.2)
    s = np.sin(2 * np.pi * 150 * t) * np.exp(-t * 28) * 0.7
    c = click(0.5)
    s[:len(c)] += c
    return s


def bloop():
    t = tt(0.16)
    f = np.linspace(600, 880, len(t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / t[-1]) * 0.22


def chime():
    s = np.zeros(int(1.0 * SR))
    for k, m in enumerate((84, 91, 96)):
        b = bell(m, 0.9) * 0.12
        i = int(k * 0.05 * SR)
        s[i:i + len(b)] += b[: len(s) - i]
    return s


def air(d=0.8):
    t = tt(d)
    return bandpass(noise(d), 600, 4000) * np.sin(np.pi * t / d) ** 2 * 0.22


# ── Music ────────────────────────────────────────────────────────────────────
CHORDS = [(53, [65, 69, 72, 76]), (48, [64, 67, 72, 74]), (50, [62, 65, 69, 72]), (46, [62, 65, 70, 74])]  # Fmaj7 C(add9) Dm7 Bbmaj7
for b in range(int(DUR / BAR)):
    t0 = b * BAR
    root, tones = CHORDS[b % 4]
    add(pad(tones, BAR + 0.6), t0, 0.32 if t0 < DROP or t0 >= OUTRO else 0.18)
    # Echoing plucks throughout; sparser before the drop.
    steps = [0, 3, 6] if t0 < DROP else [0, 2, 3, 5, 6, 8, 10, 11, 13, 14]
    for s in steps:
        m = tones[s % 4] + 12
        echo(pluck(m), t0 + s * BEAT / 4, 0.07 if t0 >= DROP else 0.1, pan=0.4)
    if t0 < DROP or t0 >= END_DRUMS:
        continue
    half = t0 >= OUTRO
    for beat in range(4):
        tb = t0 + beat * BEAT
        if not half or beat == 0:
            add(kick(), tb, 0.55)
        if beat in (1, 3):
            add(rim(), tb, 0.22, pan=0.15)
        for s16 in range(4):
            add(shaker(), tb + s16 * BEAT / 4, 0.5 if s16 % 2 else 0.25, pan=0.3)
    for e, step in enumerate([0, 3, 6, 8, 11, 14]):
        add(bass(root - 12, 0.3), t0 + step * BEAT / 4, 0.28)
    if b % 2 == 1:
        for k, m in enumerate([tones[3] + 12, tones[2] + 12, tones[1] + 12]):
            add(bell(m), t0 + 2 * BEAT + k * BEAT / 2, 0.045, pan=-0.2)

# Airy swells into each scene change and into the drop.
add(swell(1.5), DROP - 1.5, 0.6)
for c in CUTS:
    add(swell(0.9), c - 0.9, 0.35)
# Final chord.
add(pad([65, 69, 72, 76, 81], 4.5), OUTRO + 0.5, 0.22)
for k, m in enumerate([77, 81, 84, 88]):
    add(bell(m, 2.6), 38.0 + k * 0.12, 0.07, pan=-0.3 + 0.2 * k)

# Gentle sidechain so the groove breathes.
duck = np.ones(N)
for b in np.arange(DROP, END_DRUMS, BEAT):
    i = int(b * SR)
    seg = 1 - 0.18 * np.exp(-tt(0.3) * 10)
    duck[i:i + len(seg)] = np.minimum(duck[i:i + len(seg)], seg[: N - i])
L *= duck
R *= duck

# ── SFX cues (match scenes-calm.html) ────────────────────────────────────────
for t in (0.6, 0.85, 1.1, 1.5, 1.8, 2.25, 2.5, 2.95, 3.15, 3.35, 3.55, 3.75):
    add(click(), t, 0.9, pan=-0.1)
add(soft_thud(), 4.0, 0.7)
add(bloop(), 4.3, 0.7)
add(click(0.35), 6.2, 1.0)
add(chime(), 6.55, 0.9)
for c in CUTS:
    add(air(), c - 0.4, 0.5)
for a in (8.35, 9.6, 10.85, 12.1):
    add(bloop(), a + 0.1, 0.45)
    add(chime(), a + 0.65, 0.5)
add(bloop(), 14.6, 0.5); add(click(0.3), 15.0, 1.0); add(chime(), 15.6, 0.7)
add(bloop(), 16.3, 0.5); add(click(0.3), 16.9, 1.0); add(chime(), 17.3, 0.7)
add(air(0.4), 21.75, 0.5); add(chime(), 22.05, 0.7)
add(air(0.9), 23.1, 0.35); add(chime(), 24.1, 0.7)
add(air(0.4), 26.25, 0.45); add(chime(), 26.9, 0.7)
add(air(1.0), 30.95, 0.45)
add(soft_thud(), 34.55, 0.5)
for i in range(3):
    add(click(0.3), 35.0 + i * 0.4, 1.0)
add(chime(), 38.0, 0.8)

# ── Master ───────────────────────────────────────────────────────────────────
mix = np.stack([L, R])
fade = np.ones(N)
fade[: int(0.05 * SR)] = np.linspace(0, 1, int(0.05 * SR))
fo = int(2.0 * SR)
fade[-fo:] = np.linspace(1, 0, fo) ** 1.5
mix *= fade
mix /= np.max(np.abs(mix)) + 1e-9
mix = np.tanh(mix * 1.3) / np.tanh(1.3)
mix *= 10 ** (-1.0 / 20)
pcm = (mix.T * 32767).astype("<i2")

with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", sys.argv[1], f"{DUR:.1f}s")
