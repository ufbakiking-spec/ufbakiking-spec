"""Synthesises a western-style backing track that follows the voice-over's beats.

    python3 music.py  -> out/music.wav   (needs out/timeline.json from voice.py)

Plucked-guitar arpeggios (Karplus-Strong) over Am-G-F-E at 90 BPM, a low drone,
soft drums that drop out on the "silence" beat, and a whoosh + hit on every scene cut.
"""
import json
import os
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(HERE, 'out', 'timeline.json')))
SR, DUR, BPM = 44100, TL['dur'], 90
BEAT = 60 / BPM
N = int(SR * DUR)
rng = np.random.default_rng(1026)
mix = np.zeros((N, 2))
beat_at = {b['id']: b for b in TL['beats']}
CUTS = [(a['b'] + b['a']) / 2 for a, b in zip(TL['beats'], TL['beats'][1:])]


def add(sig, start, gain=1.0, pan=0.0):
    i = int(start * SR)
    if i >= N or i + len(sig) <= 0:
        return
    sig = sig[: N - i] * gain
    mix[i:i + len(sig), 0] += sig * (1 - max(pan, 0))
    mix[i:i + len(sig), 1] += sig * (1 + min(pan, 0))


def env(n, attack, decay):
    x = np.arange(n) / SR
    return np.minimum(x / attack, 1) * np.exp(-x * decay)


def smooth(x, k):
    return np.convolve(x, np.ones(k) / k, mode='same')


def pluck(freq, length=1.6, bright=.5):
    """Karplus-Strong plucked string."""
    n, p = int(length * SR), max(int(SR / freq), 2)
    buf = rng.uniform(-1, 1, p)
    buf = smooth(buf, 1 + int((1 - bright) * 4))
    out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = .4985 * (buf[i % p] + buf[(i + 1) % p])
    return out * env(n, .002, 1.2)


def kick():
    n = int(.4 * SR)
    x = np.arange(n) / SR
    return np.sin(2 * np.pi * (48 * x + 2.6 * (1 - np.exp(-30 * x)))) * env(n, .002, 8)


def shaker():
    n = int(.09 * SR)
    noise = rng.standard_normal(n)
    return (noise - smooth(noise, 3)) * env(n, .01, 45) * .2


def tom():
    n = int(.5 * SR)
    x = np.arange(n) / SR
    return (np.sin(2 * np.pi * (95 * x + 1.5 * (1 - np.exp(-20 * x)))) + .3 * smooth(rng.standard_normal(n), 8)) * env(n, .002, 7)


def whoosh(length=.55):
    n = int(length * SR)
    noise = rng.standard_normal(n)
    ramp = np.linspace(0, 1, n) ** 2
    return (smooth(noise, 30) * (1 - ramp) + (noise - smooth(noise, 5)) * ramp) * ramp * .7


def hit():
    n = int(1.2 * SR)
    x = np.arange(n) / SR
    return (np.sin(2 * np.pi * (40 * x + 5 * (1 - np.exp(-5 * x)))) * env(n, .003, 3.5) + smooth(rng.standard_normal(n), 10) * env(n, .001, 12))


def tone(freq, length, vib=0.0):
    n = int(length * SR)
    x = np.arange(n) / SR
    ph = 2 * np.pi * freq * x + (vib and (freq * .012 / 5.5) * np.sin(2 * np.pi * 5.5 * x) * 2 * np.pi)
    return np.sin(ph) * np.minimum(x / .08, 1) * np.minimum((length - x) / .25, 1).clip(0)


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


# Am - G - F - E, one chord per bar
CHORDS = [[57, 60, 64, 69], [55, 59, 62, 67], [53, 57, 60, 65], [52, 56, 59, 64]]
BAR = 4 * BEAT
sil_a, sil_b = beat_at['silence']['a'], beat_at['nate']['a']
gta_a, cta_a = beat_at['gta']['a'], beat_at['cta']['a']
drums_from = beat_at['fps']['a']

for bar in range(int(DUR / BAR) + 1):
    t0 = bar * BAR
    ch = CHORDS[bar % 4]
    # drone / bass
    add(tone(hz(ch[0] - 24), BAR + .2) + .35 * tone(hz(ch[0] - 12), BAR + .2), t0, .16)
    # guitar arpeggio, 8th notes
    pattern = [0, 2, 1, 3, 2, 1, 3, 2]
    for k, idx in enumerate(pattern):
        st = t0 + k * BEAT / 2
        quiet = sil_a - .3 < st < sil_b - .4
        if quiet and k % 2:
            continue
        add(pluck(hz(ch[idx]), 1.4, .55 if st < gta_a else .8), st, .22 if not quiet else .14, pan=(-.35, .35)[k % 2])

# drums
step = 0
t = drums_from
while t < DUR - .5:
    if not (sil_a - .2 < t < sil_b - .1):
        if step % 4 in (0, 2):
            add(kick(), t, .55)
        if step % 4 == 3 and t > gta_a:
            add(tom(), t, .25, pan=.2)
        add(shaker(), t + BEAT / 2, .9, pan=.3)
        if t > gta_a:
            add(shaker(), t + BEAT / 4, .5, pan=-.3)
    t += BEAT
    step += 1

# lonesome whistle over the hook and the outro
for (st, notes) in [(.3, [(69, .5), (76, .5), (81, 1.2), (79, .4), (76, 1.0)]), (cta_a + .2, [(69, .45), (72, .45), (76, 1.4)])]:
    for m, d in notes:
        add(tone(hz(m), d + .1, vib=1), st, .07, pan=.15)
        st += d

# wind under the "silence" beat
n = int((sil_b - sil_a) * SR)
wind = smooth(rng.standard_normal(n), 60) * np.sin(np.linspace(0, np.pi, n)) * (1 + .5 * np.sin(np.linspace(0, 9, n)))
add(wind, sil_a, .9)

for c in CUTS:
    add(whoosh(), c - .5, .35)
    add(hit(), c, .3)
add(hit(), beat_at['gta']['a'] + .1, .25)

mix = np.tanh(mix * 1.2)
mix /= np.max(np.abs(mix)) / .89
tt = np.arange(N) / SR
mix *= (np.clip(tt / .3, 0, 1) * np.clip((DUR - tt) / .8, 0, 1))[:, None]
with wave.open(os.path.join(HERE, 'out', 'music.wav'), 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes())
print('wrote out/music.wav')
