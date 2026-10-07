"""Synthesizes a 30s, 120 BPM backing track whose hits land on the video's scene cuts.

    python3 music.py  -> out/music.wav
"""
import os
import wave

import numpy as np

SR, DUR, BPM = 44100, 30.0, 120
BEAT = 60 / BPM
CUTS = [3, 7, 11, 14.25, 17.5, 22, 25]
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(1015)
mix = np.zeros((N, 2))


def add(sig, start, gain=1.0, pan=0.0):
    i = int(start * SR)
    if i >= N:
        return
    sig = sig[: N - i] * gain
    mix[i:i + len(sig), 0] += sig * (1 - max(pan, 0))
    mix[i:i + len(sig), 1] += sig * (1 + min(pan, 0))


def env(n, attack, decay):
    x = np.arange(n) / SR
    return np.minimum(x / attack, 1) * np.exp(-x * decay)


def smooth(x, k):
    return np.convolve(x, np.ones(k) / k, mode='same')


def kick():
    n = int(.45 * SR)
    x = np.arange(n) / SR
    phase = 2 * np.pi * (45 * x + (120 / 28) * (1 - np.exp(-28 * x)))
    return np.sin(phase) * env(n, .002, 7)


def clap():
    n = int(.25 * SR)
    noise = rng.standard_normal(n)
    noise = noise - smooth(noise, 6)
    return noise * env(n, .001, 22) * .5


def hat():
    n = int(.08 * SR)
    noise = rng.standard_normal(n)
    return (noise - smooth(noise, 3)) * env(n, .0005, 60) * .25


def impact():
    n = int(1.4 * SR)
    x = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (38 * x + 6 * (1 - np.exp(-6 * x)))) * env(n, .003, 3.2)
    noise = smooth(rng.standard_normal(n), 12) * env(n, .001, 9) * 1.6
    return boom + noise


def riser(length=.6):
    n = int(length * SR)
    noise = rng.standard_normal(n)
    ramp = np.linspace(0, 1, n) ** 2.5
    # crude sweep: blend from dark (heavily smoothed) to bright noise
    dark, bright = smooth(noise, 24), noise - smooth(noise, 4)
    return (dark * (1 - ramp) + bright * ramp) * ramp * .55


def note(freq, length, harmonics=4, decay=6.0):
    n = int(length * SR)
    x = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * freq * h * x) / h for h in range(1, harmonics + 1))
    return s * env(n, .004, decay)


# chord progression, one chord per bar (2s): Am - F - C - G
ROOTS = [55.0, 43.65, 65.41, 49.0]
CHORDS = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [196.0, 261.63, 329.63], [196.0, 246.94, 293.66]]

# pad: whole track, swells in
for bar in range(15):
    start = bar * 2.0
    for k, f in enumerate(CHORDS[bar % 4]):
        n = int(2.05 * SR)
        x = np.arange(n) / SR
        tone = (np.sin(2 * np.pi * f * x) + .3 * np.sin(2 * np.pi * f * 2.003 * x)) * np.minimum(x / .25, 1) * np.minimum((2.05 - x) / .2, 1)
        add(tone, start, .05 if start >= 3 else .035, pan=(k - 1) * .5)

steps = int(DUR / (BEAT / 2))
for i in range(steps):
    st = i * BEAT / 2
    on_beat = i % 2 == 0
    intro = st < 3
    if on_beat and (not intro or i % 4 == 0):
        add(kick(), st, .9)
    if not intro and i % 4 == 2:
        add(clap(), st, .6)
    if not intro and not on_beat:
        add(hat(), st, .8, pan=.3)
    if not intro or st >= 1.5:
        root = ROOTS[int(st // 2) % 4]
        add(note(root * (2 if i % 4 == 3 else 1), BEAT / 2, decay=9), st, .32)
    # arpeggio over the CTA
    if st >= 25 and st < 29.5:
        chord = CHORDS[int(st // 2) % 4]
        add(note(chord[i % 3] * 2, BEAT / 2, harmonics=2, decay=10), st, .07, pan=-.4 if i % 2 else .4)

for c in CUTS:
    add(riser(), c - .6, .5)
    add(impact(), c, .55)
add(impact(), 29.5, .7)

# master: soft clip, normalise, fade out
mix = np.tanh(mix * 1.3)
mix /= np.max(np.abs(mix)) / .89
fade = np.clip((DUR - t) / .4, 0, 1)
mix *= fade[:, None]

os.makedirs(os.path.join(os.path.dirname(__file__), 'out'), exist_ok=True)
with wave.open(os.path.join(os.path.dirname(__file__), 'out', 'music.wav'), 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes())
print('wrote out/music.wav')
