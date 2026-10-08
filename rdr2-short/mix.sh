#!/usr/bin/env bash
# Muxes a silent 1080x1920 video with the voice-over and ducked music, loudness-normalised for Shorts/TikTok.
#   ./mix.sh out/frames.mp4 RDR2_NextGen_Short.mp4
set -euo pipefail
cd "$(dirname "$0")"
ffmpeg -y -loglevel error -i "$1" -i out/vo.wav -i out/music.wav -filter_complex "
  [1:a]aresample=48000,pan=stereo|c0=c0|c1=c0,asplit[vo][key];
  [2:a]aresample=48000,volume=0.30[m];
  [m][key]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=350[md];
  [vo][md]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]" \
  -map 0:v -map '[a]' -c:v copy -c:a aac -b:a 192k -movflags +faststart -shortest "$2"
echo "wrote $2"
