"""Generates the English voice-over (Kokoro TTS) and the caption timeline.

    python3 voice.py  -> out/vo.wav, out/timeline.js, out/timeline.json

The speaking speed is solved automatically so the finished short lands on
script.json's target_seconds. Each phrase is synthesised on its own, so phrase
start/end times are exact; word times inside a phrase are spread by length.
Set KOKORO_DIR to the folder holding kokoro-v1.0.onnx and voices-v1.0.bin.
"""
import json
import os
import re
import wave

import numpy as np
from kokoro_onnx import Kokoro

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
MODEL_DIR = os.environ.get('KOKORO_DIR', os.path.join(HERE, 'work', 'kokoro'))

# how the TTS should say tokens that it would otherwise mangle (captions keep the original)
PRONOUNCE = {
    'RDR2': 'R D R 2', 'PS5': 'P S 5', 'NateTheHate': 'Nate the Hate', '4K': 'four K',
    'HDR': 'H D R', 'FPS': 'F P S', 'GTA': 'G T A', 'Talkz': 'Talks',
}
PAUSE = {',': .10, '.': .22, '?': .26, '!': .22, '...': .42}
BEAT_GAP = .26

script = json.load(open(os.path.join(HERE, 'script.json')))
kokoro = Kokoro(os.path.join(MODEL_DIR, 'kokoro-v1.0.onnx'), os.path.join(MODEL_DIR, 'voices-v1.0.bin'))
SR = 24000


def phrases(text):
    """Split a beat into phrases at , . ? ! and ellipses, keeping the delimiter."""
    out = []
    for m in re.finditer(r'(.+?)(\.\.\.|[,.?!]|$)(?=\s|$)', text.strip()):
        body, end = m.group(1).strip(), m.group(2)
        if body:
            out.append((body, end))
    return out


def say(text):
    for k, v in PRONOUNCE.items():
        text = re.sub(rf'\b{re.escape(k)}\b', v, text)
    return text


def trim(x, thr=.012):
    idx = np.where(np.abs(x) > thr)[0]
    if not len(idx):
        return x
    a, b = max(idx[0] - int(.01 * SR), 0), min(idx[-1] + int(.04 * SR), len(x))
    return x[a:b]


def synth(speed):
    clips = []
    for bi, beat in enumerate(script['beats']):
        for pi, (body, end) in enumerate(phrases(beat['text'])):
            audio, sr = kokoro.create(say(body) + (end if end in '.?!' else ''), voice=script['voice'], speed=speed, lang='en-us')
            assert sr == SR
            clips.append({'beat': bi, 'body': body, 'end': end, 'audio': trim(audio)})
    return clips


def pauses(clips):
    gaps = []
    for i, c in enumerate(clips):
        last = i == len(clips) - 1
        g = 0 if last else PAUSE.get(c['end'], .06)
        if not last and clips[i + 1]['beat'] != c['beat']:
            g = max(g, BEAT_GAP)
        gaps.append(g)
    return gaps


target, lead, tail = script['target_seconds'], script['lead_in'], script['tail']
speed = 1.0
for _ in range(3):
    clips = synth(speed)
    gaps = pauses(clips)
    speech = sum(len(c['audio']) for c in clips) / SR
    room = target - lead - tail - sum(gaps)
    print(f'speed {speed:.3f}: speech {speech:.2f}s, room {room:.2f}s')
    if abs(speech - room) < .35:
        break
    speed = float(np.clip(speed * speech / room, .8, 1.35))

# assemble; absorb what's left over into the tail so the total is exact
total_n = int(round(target * SR))
vo = np.zeros(total_n, dtype=np.float32)
t = lead
words, beats = [], []
for i, (c, g) in enumerate(zip(clips, gaps)):
    a = int(round(t * SR))
    seg = c['audio'][: max(total_n - a, 0)]
    vo[a:a + len(seg)] += seg
    dur = len(c['audio']) / SR
    toks = c['body'].split()
    w8 = [len(re.sub(r'\W', '', tok)) + 2 for tok in toks]
    acc = 0
    for tok, w in zip(toks, w8):
        words.append({'w': tok, 'a': round(t + dur * acc / sum(w8), 3), 'b': round(t + dur * (acc + w) / sum(w8), 3), 'beat': c['beat'],
                      'end': c['end'] if tok is toks[-1] else ''})
        acc += w
    if not beats or beats[-1]['i'] != c['beat']:
        beats.append({'i': c['beat'], 'id': script['beats'][c['beat']]['id'], 'a': round(t, 3)})
    beats[-1]['b'] = round(t + dur, 3)
    t += dur + g
print(f'speech ends at {t:.2f}s, total {target:.2f}s')


def captions(words):
    """Chunk words into on-screen captions (<=3 words / ~18 chars), applying spoken->caption swaps."""
    swaps = sorted(script.get('spoken_to_caption', {}).items(), key=lambda kv: -len(kv[0].split()))
    toks, i = [], 0
    norm = lambda s: re.sub(r'[^\w]', '', s).lower()
    while i < len(words):
        for k, v in swaps:
            ks = k.split()
            seq = words[i:i + len(ks)]
            if len(seq) == len(ks) and all(norm(a['w']) == norm(b) for a, b in zip(seq, ks)) and len({x['beat'] for x in seq}) == 1:
                tail_p = re.search(r'\W*$', seq[-1]['w']).group()
                toks.append({'w': v + tail_p, 'a': seq[0]['a'], 'b': seq[-1]['b'], 'beat': seq[0]['beat'], 'end': seq[-1]['end']})
                i += len(ks)
                break
        else:
            toks.append(dict(words[i]))
            i += 1
    # split each run of words between punctuation into balanced chunks of ~15 chars
    caps, run = [], []
    for k, tok in enumerate(toks):
        run.append(tok)
        nxt = toks[k + 1] if k + 1 < len(toks) else None
        if tok['end'] or not nxt or nxt['beat'] != tok['beat']:
            total = sum(len(x['w']) for x in run) + len(run) - 1
            n = max(1, round(total / 15), -(-len(run) // 3))
            goal, cur = total / n, []
            for j, x in enumerate(run):
                cur.append(x)
                if j < len(run) - 1 and (sum(len(y['w']) + 1 for y in cur) >= goal - 2 or len(cur) == 3):
                    caps.append(cur)
                    cur = []
            if cur:
                caps.append(cur)
            run = []
    caps = [{'a': c[0]['a'], 'b': c[-1]['b'], 'beat': c[0]['beat'], 'words': c} for c in caps]
    # hold each caption until the next one starts (short gaps only)
    for c, n in zip(caps, caps[1:]):
        if n['a'] - c['b'] < .5:
            c['b'] = n['a']
    return caps


tl = {'dur': target, 'beats': beats, 'words': words, 'caps': captions(words)}
os.makedirs(OUT, exist_ok=True)
json.dump(tl, open(os.path.join(OUT, 'timeline.json'), 'w'), indent=1)
open(os.path.join(OUT, 'timeline.js'), 'w').write('window.TL = ' + json.dumps(tl) + ';\n')

pcm = (np.clip(vo / max(np.max(np.abs(vo)), 1e-6) * .89, -1, 1) * 32767).astype('<i2')
with wave.open(os.path.join(OUT, 'vo.wav'), 'wb') as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
for b in beats:
    print(f"{b['id']:8s} {b['a']:6.2f} - {b['b']:6.2f}")
print('wrote out/vo.wav, out/timeline.js')
