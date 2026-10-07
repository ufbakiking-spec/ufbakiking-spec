# Arknights: Endfield — "Sanctuary of Ink" 30s Short (9:16)

A 30-second, 1080×1920 vertical promo for the TikTok Gaming Incentive Program,
built as a code-driven motion-graphics composition.

**Output:** `endfield_sanctuary_of_ink_30s.mp4` (H.264 + AAC, 30 fps)

## Storyboard (synced to a 120 BPM beat)

| Time | Scene | On screen |
|------|-------|-----------|
| 0–3s | Hook | "ENDMINISTRATOR, NEW ORDERS INCOMING" (glitch type) |
| 3–7s | Title | Ink splash on paper → *Sanctuary of Ink*, Core Chapter Update |
| 7–11s | Date | Calendar: **Oct 15, 2026**; preview livestream Oct 6 (UTC+8) |
| 11–17.5s | Operators | Operator files for **Si** and **Yeminghe** |
| 17.5–22s | Features | New main story · new region · minigames · high-difficulty content |
| 22–25s | Steam | Official **Steam debut**; PS5 / PC / Mobile / Steam |
| 25–30s | CTA | 30,000,000+ downloads → **DOWNLOAD ARKNIGHTS: ENDFIELD** → "Tap the game link below" |

Program checklist: ≥15s ✔ · clear download CTA ✔ · Endfield-focused ✔ · English text ✔.
Key text stays inside TikTok's safe area (clear of the top tabs, right-side buttons and the bottom caption/anchor link).

## Rebuilding

```bash
python3 music.py                                                       # out/music.wav
PLAYWRIGHT_MODULE=/opt/node22/lib/node_modules/playwright node render.cjs  # out/frames.mp4
ffmpeg -i out/frames.mp4 -i out/music.wav -c:v copy -c:a aac -b:a 192k -shortest endfield_sanctuary_of_ink_30s.mp4
```

Open `index.html` in a browser for a live preview (`index.html?t=12.5` freezes on one frame).
Edit text and timings in `index.html` (`build()` holds every animation keyframe).
