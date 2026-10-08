"""Footage version: cuts clips from long YouTube videos, lays the animated text,
captions and voice-over on top, and exports a finished 9:16 short.

    # 1. let it pick the clips automatically (scene detection)
    python3 clips.py --url "https://www.youtube.com/watch?v=XXXX"

    # 2. or choose the moments yourself, one per voice-over beat (11 beats)
    python3 clips.py --url URL --segments "1:02,3:40,5:10,7:55,9:30,12:00,14:20,16:45,18:10,20:00,22:30"

    # 3. already downloaded videos work too
    python3 clips.py --src long1.mp4 --src long2.mp4

Options: --fit fill (crop to full screen, default) | blur (whole 16:9 frame over a blurred copy)
         --keep-audio 0.08 (mix the clip's own game audio in quietly; default 0 = muted)
Needs: yt-dlp (pip install yt-dlp), ffmpeg, and the out/ files from build.sh
(vo.wav, music.wav, timeline.json). The overlay is rendered on first use.
Only use footage you own or have the creator's permission for.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT, WORK = os.path.join(HERE, 'out'), os.path.join(HERE, 'work', 'clips')
W, H, FPS = 1080, 1920, 30


def run(cmd, **kw):
    print('+', ' '.join(cmd)[:160])
    return subprocess.run(cmd, check=True, **kw)


def seconds(s):
    parts = [float(p) for p in s.strip().split(':')]
    return sum(p * 60 ** i for i, p in enumerate(reversed(parts)))


def duration(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def download(url, idx):
    os.makedirs(WORK, exist_ok=True)
    out = os.path.join(WORK, f'src{idx}.mp4')
    if not os.path.exists(out):
        run([sys.executable, '-m', 'yt_dlp', '-f', 'bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]/b',
             '--merge-output-format', 'mp4', '-o', out, url])
    return out


def scene_cuts(path):
    """Timestamps where the picture changes a lot (analysed at low res for speed)."""
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', path, '-vf', "scale=320:-2,select='gt(scene,0.35)',showinfo", '-an', '-f', 'null', '-'],
                       capture_output=True, text=True)
    return [float(m) for m in re.findall(r'pts_time:([\d.]+)', r.stderr)]


def auto_pick(sources, durs):
    """One start time per beat: scene cuts spread evenly over the middle 84% of the sources."""
    picks = []
    per = [len(durs) // len(sources) + (1 if i < len(durs) % len(sources) else 0) for i in range(len(sources))]
    k = 0
    for src, count in zip(sources, per):
        total = duration(src)
        lo, hi = total * .08, total * .92
        cuts = [c for c in scene_cuts(src) if lo < c < hi - 8] or [lo + (hi - lo) * i / max(count, 1) for i in range(count)]
        for j in range(count):
            target = lo + (hi - lo) * (j + .5) / count
            start = min(cuts, key=lambda c: abs(c - target)) + .15
            picks.append((src, min(start, total - durs[k] - .1)))
            k += 1
    return picks


def cut(src, start, dur, i, fit):
    out = os.path.join(WORK, f'part{i:02d}.mp4')
    if fit == 'blur':
        vf = (f'[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:2,eq=brightness=-.12[bg];'
              f'[b]scale={W}:-2[fg];[bg][fg]overlay=0:(H-h)/2-120,fps={FPS},setsar=1[v]')
    else:
        # fill the frame; a slow push-in keeps static shots alive
        vf = (f'[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},'
              f"scale=w='2*trunc({W}*(1+0.06*t/{dur:.2f})/2)':h=-2:eval=frame,crop={W}:{H},fps={FPS},setsar=1,eq=saturation=1.08:contrast=1.04[v]")
    run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{start:.3f}', '-t', f'{dur:.3f}', '-i', src, '-filter_complex', vf,
         '-map', '[v]', '-map', '0:a?', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-c:a', 'aac', '-ar', '48000', '-ac', '2', out])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--url', action='append', default=[], help='YouTube link (repeatable)')
    ap.add_argument('--src', action='append', default=[], help='local video file (repeatable)')
    ap.add_argument('--segments', help='comma-separated start times, one per beat (e.g. 1:02,3:40,...)')
    ap.add_argument('--fit', choices=['fill', 'blur'], default='fill')
    ap.add_argument('--keep-audio', type=float, default=0.0)
    ap.add_argument('-o', '--output', default=os.path.join(HERE, 'RDR2_NextGen_Short_clips.mp4'))
    a = ap.parse_args()

    sources = a.src + [download(u, i) for i, u in enumerate(a.url)]
    if not sources:
        ap.error('give at least one --url or --src')
    tl = json.load(open(os.path.join(OUT, 'timeline.json')))
    beats = tl['beats']
    # each beat's clip spans its scene (scene borders sit halfway between beats, like index.html)
    edges = [0] + [(x['b'] + y['a']) / 2 for x, y in zip(beats, beats[1:])] + [tl['dur']]
    durs = [b - a_ for a_, b in zip(edges, edges[1:])]

    if a.segments:
        starts = [seconds(s) for s in a.segments.split(',')]
        if len(starts) != len(durs):
            ap.error(f'--segments needs {len(durs)} start times (one per beat), got {len(starts)}')
        picks = [(sources[min(i * len(sources) // len(durs), len(sources) - 1)], s) for i, s in enumerate(starts)]
    else:
        picks = auto_pick(sources, durs)

    os.makedirs(WORK, exist_ok=True)
    parts = []
    for i, ((src, start), d) in enumerate(zip(picks, durs)):
        print(f'beat {beats[i]["id"]:8s} <- {os.path.basename(src)} @ {start:7.2f}s for {d:.2f}s')
        parts.append(cut(src, start, d, i, a.fit))
    listing = os.path.join(WORK, 'parts.txt')
    open(listing, 'w').write(''.join(f"file '{p}'\n" for p in parts))
    footage = os.path.join(WORK, 'footage.mp4')
    run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', listing, '-c', 'copy', footage])

    overlay = os.path.join(OUT, 'overlay.mov')
    if not os.path.exists(overlay):
        run(['node', os.path.join(HERE, 'render.cjs'), '--overlay'])

    game = f'[0:a]volume={a.keep_audio}[g];' if a.keep_audio > 0 else ''
    voice_mix = '[vo][md][g]amix=inputs=3:normalize=0' if a.keep_audio > 0 else '[vo][md]amix=inputs=2:normalize=0'
    run(['ffmpeg', '-y', '-loglevel', 'error', '-i', footage, '-i', overlay, '-i', os.path.join(OUT, 'vo.wav'), '-i', os.path.join(OUT, 'music.wav'),
         '-filter_complex',
         f'[0:v][1:v]overlay=0:0:shortest=1,format=yuv420p[v];'
         f'[2:a]aresample=48000,pan=stereo|c0=c0|c1=c0,asplit[vo][key];[3:a]aresample=48000,volume=0.22[m];'
         f'[m][key]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=350[md];{game}'
         f'{voice_mix},loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]',
         '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-c:a', 'aac', '-b:a', '192k',
         '-movflags', '+faststart', '-t', str(tl['dur']), a.output])
    print('wrote', a.output)


if __name__ == '__main__':
    main()
