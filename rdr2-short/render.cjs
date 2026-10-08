// Renders index.html frame-by-frame with Playwright and pipes the frames into ffmpeg.
//   node render.cjs                    -> out/frames.mp4   (full video, silent; WORKERS=3 pages in parallel)
//   node render.cjs --overlay          -> out/overlay.mov  (text/captions only, with alpha, for laying over clips)
//   node render.cjs --stills 1,5,12.5  -> out/still_<t>.png for quick review
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const FPS = 30, W = 1080, H = 1920;
const here = __dirname, outDir = path.join(here, 'out');
fs.mkdirSync(outDir, { recursive: true });
const overlay = process.argv.includes('--overlay');

(async () => {
  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(here, 'index.html') + (overlay ? '?overlay=1' : ''));
  await page.evaluate(() => window.__ready);
  const DUR = await page.evaluate(() => window.TL.dur);
  const stage = await page.$('#stage');
  const shot = () => stage.screenshot({ type: 'png', omitBackground: overlay });

  const stillsArg = process.argv.indexOf('--stills');
  if (stillsArg > -1) {
    for (const t of process.argv[stillsArg + 1].split(',').map(Number)) {
      await page.evaluate(t => window.render(t), t);
      fs.writeFileSync(path.join(outDir, `still_${t}${overlay ? '_ov' : ''}.png`), await shot());
    }
    await browser.close();
    return;
  }

  // split the frames across several pages rendering in parallel, one ffmpeg per chunk, then concat
  const total = Math.round(FPS * DUR);
  const workers = +(process.env.WORKERS || 3);
  const ext = overlay ? 'mov' : 'mp4';
  const enc = overlay
    ? ['-c:v', 'qtrle']
    : ['-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p'];
  const per = Math.ceil(total / workers);
  let done = 0;
  const chunk = async k => {
    const p = k === 0 ? page : await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
    if (k) { await p.goto(page.url()); await p.evaluate(() => window.__ready); }
    const st = await p.$('#stage');
    const file = path.join(outDir, `chunk${k}.${ext}`);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', overlay ? 'png' : 'mjpeg', '-i', '-', ...enc, file],
      { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let f = k * per; f < Math.min(total, (k + 1) * per); f++) {
      await p.evaluate(t => window.render(t), f / FPS);
      const buf = await st.screenshot(overlay ? { type: 'png', omitBackground: true } : { type: 'jpeg', quality: 95 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (++done % 150 === 0) console.log(`frame ${done}/${total}`);
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
    return file;
  };
  const files = await Promise.all([...Array(workers).keys()].map(chunk));
  const list = path.join(outDir, 'chunks.txt');
  fs.writeFileSync(list, files.map(f => `file '${f}'`).join('\n'));
  const out = path.join(outDir, overlay ? 'overlay.mov' : 'frames.mp4');
  await new Promise(r => spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', out], { stdio: 'inherit' }).on('close', r));
  files.forEach(f => fs.unlinkSync(f));
  await browser.close();
  console.log('done');
})();
