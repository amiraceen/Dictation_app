"""Synthesises the promo soundtrack: an upbeat 120 BPM groove plus UI sound effects
timed to the scene cues in scenes.html. Pure numpy, no samples.

    python3 music.py out.wav
"""
import sys
import wave
import numpy as np

SR = 48000
BPM = 120
BEAT = 60 / BPM            # 0.5 s
BAR = 4 * BEAT             # 2 s
DUR = 44.0
DROP = 4.0                 # beat drops when Right ⌥ is pressed
END_DRUMS = 42.0

rng = np.random.default_rng(7)
N = int(DUR * SR)
L = np.zeros(N)
R = np.zeros(N)


def add(sig, t, gain=1.0, pan=0.0):
    """Mix a mono signal in at time t (s), pan -1..1."""
    i = int(t * SR)
    if i >= N or i + len(sig) <= 0:
        return
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


# ── Instruments ──────────────────────────────────────────────────────────────
def kick():
    t = tt(0.4)
    f = 45 + 95 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 7.5) + 0.25 * np.sin(ph * 2) * np.exp(-t * 30)


def clap():
    t = tt(0.25)
    n = rng.standard_normal(len(t))
    env = np.exp(-t * 22)
    for off in (0.0, 0.011, 0.022):
        env += 0.6 * np.exp(-np.clip(t - off, 0, None) * 120) * (t >= off)
    return bandpass(n * env, 900, 5000) * 0.6


def hat(open_=False):
    t = tt(0.18 if open_ else 0.05)
    n = rng.standard_normal(len(t))
    n = np.diff(np.diff(n, prepend=0), prepend=0)
    return n * np.exp(-t * (18 if open_ else 80)) * 0.18


def pluck(m, d=0.45):
    t = tt(d)
    f = hz(m)
    s = sum(np.sin(2 * np.pi * f * k * t) / k ** 1.3 * np.exp(-t * (6 + 5 * k)) for k in range(1, 6))
    return s * np.minimum(1, t * 400)


def bass(m, d):
    t = tt(d)
    f = hz(m)
    s = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 5))
    env = np.minimum(1, t * 300) * np.exp(-t * 3.0) * np.minimum(1, (d - t) * 60)
    return s * env


def pad(ms, d):
    t = tt(d)
    s = np.zeros(len(t))
    for m in ms:
        for det in (-0.12, 0.0, 0.12):
            f = hz(m + det)
            s += sum(np.sin(2 * np.pi * f * k * t + rng.uniform(0, 6)) / k ** 1.8 for k in range(1, 4))
    env = np.minimum(1, t / 0.5) * np.minimum(1, (d - t) / 0.4)
    return s * env / (len(ms) * 3)


def bell(m, d=1.2):
    t = tt(d)
    f = hz(m)
    return (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6)) * np.exp(-t * 3.2)


# ── SFX ──────────────────────────────────────────────────────────────────────
def keyclick(soft=False):
    t = tt(0.04)
    n = bandpass(rng.standard_normal(len(t)), 1800, 7000)
    return n * np.exp(-t * 160) * (0.35 if soft else 0.55)


def thock():
    t = tt(0.12)
    s = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 45) * 0.8
    c = keyclick()
    s[:len(c)] += c * 0.8
    return s


def bloop(up=True):
    t = tt(0.12)
    f = np.linspace(520, 880, len(t)) if up else np.linspace(880, 520, len(t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / t[-1]) * 0.35


def sparkle():
    s = np.zeros(int(0.6 * SR))
    for k, m in enumerate((88, 95, 100)):
        b = bell(m, 0.5) * 0.18
        i = int(k * 0.045 * SR)
        s[i:i + len(b)] += b[: len(s) - i]
    return s


def whoosh(d=0.55):
    t = tt(d)
    n = rng.standard_normal(len(t))
    out = np.zeros(len(t))
    seg = 1024
    for i in range(0, len(t), seg):
        c = 400 + 3600 * (i / len(t))
        out[i:i + seg] = bandpass(n[i:i + seg], c * 0.5, c * 1.5)[: len(out[i:i + seg])]
    return out * np.sin(np.pi * t / d) ** 2 * 0.5


def swish():
    t = tt(0.22)
    return bandpass(rng.standard_normal(len(t)), 2500, 9000) * np.sin(np.pi * t / t[-1]) * 0.35


def pop():
    t = tt(0.08)
    f = np.linspace(900, 420, len(t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 40) * 0.35


# ── Music ────────────────────────────────────────────────────────────────────
# F – C – Dm – Bb (I V vi IV), one chord per bar.
CHORDS = [(53, [65, 69, 72]), (48, [64, 67, 72]), (50, [62, 65, 69]), (46, [62, 65, 70])]
bars = int(DUR / BAR)
for b in range(bars):
    t0 = b * BAR
    root, tones = CHORDS[b % 4]
    # Pad throughout (louder in intro and outro).
    add(pad(tones, BAR + 0.3), t0, 0.45 if t0 < DROP else (0.22 if t0 >= 38 else 0.14))
    if t0 < DROP:
        # Intro: sparse plucks only.
        for k in (0, 3, 6):
            add(pluck(tones[k % 3] + 12, 0.6), t0 + k * BEAT / 2, 0.24, pan=-0.3 + 0.3 * k / 3)
        continue
    if t0 >= END_DRUMS:
        continue
    for beat in range(4):
        tb = t0 + beat * BEAT
        add(kick(), tb, 0.85)
        if beat in (1, 3):
            add(clap(), tb, 0.5, pan=0.05)
        add(hat(), tb + BEAT / 2, 0.9, pan=0.25)
        add(hat(), tb + BEAT / 4, 0.35, pan=0.3)
        add(hat(), tb + 3 * BEAT / 4, 0.35, pan=0.3)
    # Bass on eighths with an octave hop.
    for e in range(8):
        m = root - 12 + (12 if e in (3, 6) else 0)
        add(bass(m, BEAT / 2 - 0.02), t0 + e * BEAT / 2, 0.30)
    # Arpeggiated plucks in sixteenths.
    pattern = [0, 1, 2, 1, 0, 2, 1, 2]
    for s in range(16):
        m = tones[pattern[s % 8]] + (12 if s >= 8 and s % 3 == 0 else 0)
        add(pluck(m + 12, 0.35), t0 + s * BEAT / 4, 0.10, pan=(-0.45 if s % 2 else 0.45))
    # Bell hook every other bar.
    if b % 2 == 1:
        for k, m in enumerate([tones[2] + 12, tones[1] + 12, tones[0] + 12]):
            add(bell(m, 0.9), t0 + 2 * BEAT + k * BEAT / 2, 0.07, pan=0.2)

# Final ringing chord + a logo chime.
add(pad([65, 69, 72, 77], 5.5), 38.5, 0.22)
for k, m in enumerate([77, 81, 84, 89]):
    add(bell(m, 2.5), 39.1 + k * 0.09, 0.10, pan=-0.3 + 0.2 * k)

# Sidechain: duck everything but the kick slightly on each beat after the drop.
duck = np.ones(N)
for b in np.arange(DROP, END_DRUMS, BEAT):
    i = int(b * SR)
    t = tt(0.3)
    seg = 1 - 0.35 * np.exp(-t * 12)
    duck[i:i + len(seg)] = np.minimum(duck[i:i + len(seg)], seg[: N - i])
L *= duck
R *= duck

# ── SFX cues (match scenes.html) ─────────────────────────────────────────────
for t in (0.7, 1.0, 1.35, 1.85, 2.2, 2.75, 3.1, 3.35, 3.55, 3.8):
    add(keyclick(soft=True), t, 1.6, pan=-0.1)
add(thock(), 4.0, 0.9)                      # Right ⌥ down
add(bloop(True), 4.02, 0.8)                 # recording bar appears
add(keyclick(), 6.2, 0.7)                   # key released
add(sparkle(), 6.6, 1.0)                    # text typed
for t in (8.0, 14.0, 20.0, 22.75, 25.35, 28.0, 34.0, 38.5):
    add(whoosh(), t - 0.3, 0.55)
for r, w in [(9.0, 9.55), (10.15, 10.7), (11.3, 11.85), (12.45, 13.0)]:
    add(bloop(True), r, 0.55)
    add(sparkle(), w, 0.6)
add(bloop(True), 14.7, 0.6); add(sparkle(), 16.05, 0.8)
add(bloop(True), 16.6, 0.6); add(sparkle(), 17.85, 0.8)
for i in range(5):
    add(pop(), 18.3 + i * 0.16, 0.6, pan=-0.4 + 0.2 * i)
add(swish(), 21.0, 0.8); add(sparkle(), 21.55, 0.8)
add(pop(), 23.4, 0.7); add(sparkle(), 24.05, 0.8)
add(swish(), 26.1, 0.7); add(swish(), 26.3, 0.7); add(sparkle(), 26.75, 0.8)
add(pop(), 30.2, 0.6); add(whoosh(0.7), 30.9, 0.5)
add(thock(), 34.7, 0.6)
for i in range(3):
    add(pop(), 35.4 + i * 0.3, 0.6, pan=-0.3 + 0.3 * i)

# ── Master ───────────────────────────────────────────────────────────────────
mix = np.stack([L, R])
fade = np.ones(N)
fade[: int(0.05 * SR)] = np.linspace(0, 1, int(0.05 * SR))
fo = int(2.0 * SR)
fade[-fo:] = np.linspace(1, 0, fo) ** 1.5
mix *= fade
mix /= np.max(np.abs(mix)) + 1e-9
mix = np.tanh(mix * 1.4) / np.tanh(1.4)
mix *= 10 ** (-1.0 / 20)
pcm = (mix.T * 32767).astype("<i2")

with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", sys.argv[1], f"{DUR:.1f}s")
