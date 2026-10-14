"""Soundtrack for the Arabic vertical promo (scenes-ar.html), 66 s. Same groove as the dynamic cut: a punchier 120 BPM groove with a riser
into the drop, fills and crashes on every cut, offbeat stabs, and UI sound effects
timed to scenes-vertical.html. Pure numpy, no samples.

    python3 music_ar.py out.wav
"""
import sys
import wave
import numpy as np

SR = 48000
BEAT = 0.5                 # 120 BPM
BAR = 4 * BEAT
DUR = 66.0
DROP = 4.0                 # Right ⌥ pressed: the groove starts
OUTRO = 60.0               # end card, half-time
END_DRUMS = 64.0
CUTS = [12.0, 20.0, 26.0, 32.0, 40.0, 46.0, 54.0]   # every section change lands on a 2 s bar

rng = np.random.default_rng(11)
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
    t = tt(0.4)
    f = 48 + 110 * np.exp(-t * 30)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 7) + 0.3 * np.sin(ph * 2) * np.exp(-t * 35)


def snare(g=1.0):
    t = tt(0.22)
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.5
    return (body + bandpass(noise(0.22), 1200, 8000) * np.exp(-t * 18) * 0.7) * g


def clap():
    t = tt(0.25)
    env = np.exp(-t * 22)
    for off in (0.0, 0.011, 0.022):
        env += 0.6 * np.exp(-np.clip(t - off, 0, None) * 120) * (t >= off)
    return bandpass(noise(0.25) * env, 900, 5000) * 0.6


def hat(open_=False):
    t = tt(0.22 if open_ else 0.05)
    n = np.diff(np.diff(noise(len(t) / SR), prepend=0), prepend=0)
    return n * np.exp(-t * (14 if open_ else 80)) * 0.18


def crash():
    t = tt(1.6)
    return bandpass(noise(1.6), 3000, 14000) * np.exp(-t * 2.6) * 0.5


def pluck(m, d=0.35):
    t = tt(d)
    f = hz(m)
    s = sum(np.sin(2 * np.pi * f * k * t) / k ** 1.3 * np.exp(-t * (6 + 5 * k)) for k in range(1, 6))
    return s * np.minimum(1, t * 400)


def stab(ms, d=0.16):
    t = tt(d)
    s = sum(sum(np.sin(2 * np.pi * hz(m + det) * k * t) / k for k in range(1, 6)) for m in ms for det in (-0.08, 0.08))
    return s * np.exp(-t * 14) * np.minimum(1, t * 500) / (len(ms) * 2)


def bass(m, d):
    t = tt(d)
    s = sum(np.sin(2 * np.pi * hz(m) * k * t) / k for k in range(1, 5))
    return s * np.minimum(1, t * 300) * np.exp(-t * 2.5) * np.minimum(1, (d - t) * 60)


def pad(ms, d):
    t = tt(d)
    s = np.zeros(len(t))
    for m in ms:
        for det in (-0.12, 0.0, 0.12):
            s += sum(np.sin(2 * np.pi * hz(m + det) * k * t + rng.uniform(0, 6)) / k ** 1.8 for k in range(1, 4))
    return s * np.minimum(1, t / 0.4) * np.minimum(1, (d - t) / 0.4) / (len(ms) * 3)


def bell(m, d=1.0):
    t = tt(d)
    f = hz(m)
    return (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6)) * np.exp(-t * 3.2)


# ── SFX ──────────────────────────────────────────────────────────────────────
def keyclick(g=0.55):
    t = tt(0.04)
    return bandpass(noise(0.04), 1800, 7000) * np.exp(-t * 160) * g


def thock(g=1.0):
    t = tt(0.14)
    s = np.sin(2 * np.pi * 170 * t) * np.exp(-t * 40) * 0.8
    c = keyclick()
    s[:len(c)] += c * 0.8
    return s * g


def boom():
    t = tt(0.9)
    f = 30 + 70 * np.exp(-t * 8)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.5)


def bloop():
    t = tt(0.12)
    f = np.linspace(520, 900, len(t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / t[-1]) * 0.35


def sparkle():
    s = np.zeros(int(0.6 * SR))
    for k, m in enumerate((88, 95, 100)):
        b = bell(m, 0.5) * 0.18
        i = int(k * 0.04 * SR)
        s[i:i + len(b)] += b[: len(s) - i]
    return s


def whip(d=0.32):
    t = tt(d)
    n = noise(d)
    out = np.zeros(len(t))
    seg = 512
    for i in range(0, len(t), seg):
        c = 600 + 5000 * np.sin(np.pi * i / len(t))
        out[i:i + seg] = bandpass(n[i:i + seg], c * 0.5, c * 1.6)[: len(out[i:i + seg])]
    return out * np.sin(np.pi * t / d) ** 2 * 0.6


def riser(d):
    t = tt(d)
    n = noise(d)
    out = np.zeros(len(t))
    seg = 1024
    for i in range(0, len(t), seg):
        c = 300 + 6000 * (i / len(t)) ** 2
        out[i:i + seg] = bandpass(n[i:i + seg], c * 0.6, c * 1.4)[: len(out[i:i + seg])]
    return out * (t / d) ** 2 * 0.5


def pop():
    t = tt(0.08)
    f = np.linspace(950, 420, len(t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 40) * 0.4


def swish():
    t = tt(0.2)
    return bandpass(noise(0.2), 2500, 9000) * np.sin(np.pi * t / t[-1]) * 0.35


# ── Music ────────────────────────────────────────────────────────────────────
CHORDS = [(53, [65, 69, 72]), (48, [64, 67, 72]), (50, [62, 65, 69]), (46, [62, 65, 70])]   # F C Dm Bb
for b in range(int(DUR / BAR)):
    t0 = b * BAR
    root, tones = CHORDS[b % 4]
    if t0 < DROP:
        add(pad(tones, BAR + 0.3), t0, 0.45)
        for k in (0, 3, 6):
            add(pluck(tones[k % 3] + 12, 0.6), t0 + k * BEAT / 2, 0.24, pan=-0.3 + 0.2 * k)
        continue
    half = t0 >= OUTRO
    add(pad(tones, BAR + 0.3), t0, 0.22 if half else 0.12)
    if t0 >= END_DRUMS:
        continue
    for beat in range(4):
        tb = t0 + beat * BEAT
        if not half or beat in (0, 2):
            add(kick(), tb, 0.9)
        if beat in (1, 3) and not half:
            add(clap(), tb, 0.45, pan=0.05); add(snare(0.35), tb, 1.0)
        if half and beat == 2:
            add(clap(), tb, 0.4)
        if not half:
            add(hat(open_=True), tb + BEAT / 2, 0.7, pan=0.3)
            for s16 in (1, 3):
                add(hat(), tb + s16 * BEAT / 4, 0.45 + 0.15 * (s16 == 3), pan=0.25)
            # Offbeat stabs on the "and" of 2 and 4.
            if beat in (1, 3):
                add(stab([m + 12 for m in tones]), tb + BEAT / 2, 0.16, pan=-0.2)
    # Syncopated bass.
    for e, (step, oct_) in enumerate([(0, 0), (3, 0), (6, 12), (8, 0), (11, 0), (14, 12)]):
        add(bass(root - 12 + oct_, 0.22), t0 + step * BEAT / 4, 0.32 if not half else 0.22)
    if not half:
        pattern = [0, 1, 2, 1, 0, 2, 1, 2]
        for s in range(16):
            m = tones[pattern[s % 8]] + (12 if s >= 8 and s % 3 == 0 else 0)
            add(pluck(m + 12, 0.3), t0 + s * BEAT / 4, 0.09, pan=(-0.5 if s % 2 else 0.5))
    if b % 2 == 1 or half:
        for k, m in enumerate([tones[2] + 12, tones[1] + 12, tones[0] + 12, tones[1] + 24]):
            add(bell(m, 0.9), t0 + 2 * BEAT + k * BEAT / 2, 0.08, pan=0.2)

# Snare-roll fills into every cut, crash on the downbeat.
for c in [DROP] + CUTS + [OUTRO]:
    n = 8 if c == DROP else 4
    for k in range(n):
        tk = c - (n - k) * BEAT / 4
        add(snare(0.25 + 0.6 * k / n), tk, 1.0, pan=0.1 * (-1) ** k)
    add(crash(), c, 0.55)
add(riser(2.0), DROP - 2.0, 0.8)
add(riser(1.0), OUTRO - 1.0, 0.5)
add(pad([65, 69, 72, 77], 8.0), OUTRO, 0.2)

# Sidechain duck on each kick after the drop.
duck = np.ones(N)
for b in np.arange(DROP, END_DRUMS, BEAT):
    i = int(b * SR)
    seg = 1 - 0.38 * np.exp(-tt(0.3) * 12)
    duck[i:i + len(seg)] = np.minimum(duck[i:i + len(seg)], seg[: N - i])
L *= duck
R *= duck

# ── SFX cues (match scenes-ar.html) ───────────────────────────────────────
for t in (0.6, 0.85, 1.1, 1.5, 1.8, 2.25, 2.5, 2.95, 3.15, 3.35, 3.55, 3.75):
    add(keyclick(0.9), t, 1.0, pan=-0.1)
add(whip(0.4), 3.1, 0.5)                    # key glides in
add(thock(), 4.0, 1.0); add(boom(), 4.0, 0.6); add(bloop(), 4.1, 0.8)
add(keyclick(), 6.6, 0.8)
add(sparkle(), 7.0, 1.0)
for c in CUTS + [OUTRO]:
    add(whip(0.8), c - 0.4, 0.6)            # parallax slide
for a in (12.5, 14.4, 16.3, 18.2):          # app cards land (burst)
    add(whip(0.3), a - 0.05, 0.35, pan=0.3)
    add(pop(), a + 0.05, 0.7)
    add(bloop(), a + 0.2, 0.45)
    add(sparkle(), a + 0.8, 0.5)
add(bloop(), 20.6, 0.6); add(thock(0.5), 21.0, 1.0); add(pop(), 21.7, 0.8); add(sparkle(), 21.7, 0.7)
add(bloop(), 22.3, 0.6); add(thock(0.5), 23.0, 1.0); add(pop(), 23.4, 0.8); add(sparkle(), 23.4, 0.7)
for i in range(5):
    add(pop(), 24.0 + i * 0.15, 0.6, pan=-0.4 + 0.2 * i)
for a in (27.2, 27.7, 28.2):
    add(pop(), a, 0.7)
add(swish(), 28.6, 0.9); add(thock(0.7), 29.0, 1.0); add(sparkle(), 29.0, 0.8)
add(whip(0.6), 33.0, 0.4); add(pop(), 34.0, 0.7)            # zoom to the Shortcuts menu, lens
add(whip(0.7), 35.4, 0.4); add(pop(), 36.6, 0.7)            # pan to the row, lens
add(pop(), 37.4, 0.6); add(thock(0.6), 38.4, 1.0); add(sparkle(), 38.4, 0.8)
for i in range(6):
    add(pop(), 40.6 + i * 0.1, 0.4)
add(pop(), 41.6, 1.0); add(pop(), 41.8, 1.0)
add(swish(), 42.6, 0.6); add(sparkle(), 43.3, 0.6)
add(thock(0.6), 44.4, 1.0); add(pop(), 44.4, 0.8); add(sparkle(), 44.4, 0.8)
for a in (46.6, 47.2, 47.8, 48.4, 49.0):
    add(swish(), a, 0.6, pan=0.2); add(pop(), a + 0.05, 0.6)
add(pop(), 49.7, 0.6); add(whip(0.6), 50.3, 0.5)
add(thock(), 54.7, 1.0); add(boom(), 54.7, 0.5)
for i in range(3):
    add(thock(0.7), 55.4 + i * 0.5, 1.0, pan=-0.2 + 0.2 * i); add(pop(), 55.4 + i * 0.5, 0.6)
for k, m in enumerate([77, 81, 84, 89]):
    add(bell(m, 2.5), 60.6 + k * 0.08, 0.11, pan=-0.3 + 0.2 * k)
add(pop(), 61.0, 0.6)

# ── Master ───────────────────────────────────────────────────────────────────
mix = np.stack([L, R])
fade = np.ones(N)
fade[: int(0.05 * SR)] = np.linspace(0, 1, int(0.05 * SR))
fo = int(2.5 * SR)
fade[-fo:] = np.linspace(1, 0, fo) ** 1.5
mix *= fade
mix /= np.max(np.abs(mix)) + 1e-9
mix = np.tanh(mix * 1.6) / np.tanh(1.6)
mix *= 10 ** (-1.0 / 20)
pcm = (mix.T * 32767).astype("<i2")

with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", sys.argv[1], f"{DUR:.1f}s")
