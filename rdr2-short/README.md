# RDR2 Short: "Where Is the RDR2 Next-Gen Upgrade?" (61s, 9:16)

A 61-second, 1080×1920 YouTube Shorts / TikTok / Reels explainer with an English AI voice-over,
word-by-word captions, animated on-screen text and a western-style music track.

**Output:** `RDR2_NextGen_Short.mp4` (H.264 + AAC, 30 fps, -14 LUFS)

## Why this topic (researched Oct 8, 2026)

- RDR2 turns **8 on Oct 26, 2026** and still has no native PS5 / Xbox Series X version. It runs at 30 FPS through backward compatibility.
- The original RDR got a current-gen release in **Dec 2025** (60 FPS, 4K, HDR), so fans expected RDR2 next.
- Insiders disagree on timing. **NateTheHate** says the upgrade exists and was planned for 2026, but he has "no update on timing". **Kiwi Talkz** says it could slip to late 2027. A **June 2026** report says it may be finished but held back.
- **GTA VI** launches in **November 2026**, which is the likely reason Rockstar is waiting.
- The **Red Dead Online Halloween** event is live from Oct 6 to Nov 2: 4X rewards on Strange Tales of the West and 3X on All Hallows' Call to Arms.

All of this is rumour except the RDR1 release, GTA VI's date and the RDO event. The script says "insider says" and "report claims" on purpose.

## Storyboard (timings come from the voice-over)

| Time | Beat | On screen |
|------|------|-----------|
| 0–3.4 | Hook | Revolver cylinder, "8 YEARS OLD", Oct 26 2018 → 2026 |
| 3.4–8.5 | 30 FPS | Red "30 FPS" counter stuck, "STILL" stamp |
| 8.5–12.1 | Question | WANTED poster: "RDR2 Next-Gen Upgrade ?" |
| 12.1–21.3 | RDR1 | Dec 2025 chip, 60 FPS / 4K / HDR tiles |
| 21.3–25.4 | Silence | "Arthur Next?" fades, "...", tumbleweed (the music drops out) |
| 25.4–31.4 | Insider 1 | NateTheHate dossier |
| 31.4–36.9 | Insider 2 | Kiwi Talkz dossier, timeline slides to LATE 2027 |
| 36.9–41.8 | Finished? | Build bar fills to 100%, "ON HOLD" stamp |
| 41.8–48.0 | GTA VI | Neon "GTA VI" under a spotlight, "Launches Nov 2026" |
| 48.0–55.9 | RDO | Halloween, "Live until Nov 2", big 4X |
| 55.9–61.0 | CTA | "Would you buy it again?" YES / NO, "Comment below" |

Text stays inside the Shorts/TikTok safe area, away from the top bar, the right-hand buttons and the bottom title area.

## Rebuild

```bash
pip install kokoro-onnx soundfile numpy
# put kokoro-v1.0.onnx + voices-v1.0.bin (github.com/thewh1teagle/kokoro-onnx releases) in work/kokoro/
./build.sh        # voice -> music -> render -> mix  =>  RDR2_NextGen_Short.mp4
```

To make a new short, edit `script.json` (beats, voice, target length) and the matching scene cards in
`index.html`. All animation timings follow the words, so a new voice-over keeps everything in sync.
Other voices: `am_adam`, `am_onyx`, `am_fenrir`, `bm_george`, `bm_lewis` and more.
Open `index.html?t=12.5` in a browser to check a single frame.

## Version with a YouTuber's clips

`clips.py` downloads long videos, picks one clip per beat (by scene detection, or at the times you
choose), crops them to 9:16, and lays the same captions, text and voice-over on top.

```bash
pip install yt-dlp
python3 clips.py --url "https://www.youtube.com/watch?v=XXXX"                 # auto-pick clips
python3 clips.py --url URL --segments "1:02,3:40,5:10,7:55,9:30,12:00,14:20,16:45,18:10,20:00,22:30"
python3 clips.py --src my_gameplay.mp4 --fit blur --keep-audio 0.08
```

Only use footage you recorded yourself or have the creator's permission to use. Otherwise
YouTube can issue a copyright claim or strike.
