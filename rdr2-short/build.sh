#!/usr/bin/env bash
# Full pipeline for the motion-graphics version: script.json -> finished 9:16 short.
set -euo pipefail
cd "$(dirname "$0")"
export PLAYWRIGHT_MODULE=${PLAYWRIGHT_MODULE:-/opt/node22/lib/node_modules/playwright}
python3 voice.py          # out/vo.wav + out/timeline.js
python3 music.py          # out/music.wav
node render.cjs           # out/frames.mp4
./mix.sh out/frames.mp4 RDR2_NextGen_Short.mp4
