// Renders index.html frame-by-frame with Playwright and pipes the frames into ffmpeg.
//   node render.cjs                       -> out/frames.mp4 (silent, 30s @ 30fps)
//   node render.cjs --stills 1,5,12.5     -> out/still_<t>.png for quick review
const path = require('path');
const { spawn } = require('child_process');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const FPS = 30, DUR = 30, W = 1080, H = 1920;
const here = __dirname;
const outDir = path.join(here, 'out');
require('fs').mkdirSync(outDir, { recursive: true });

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(here, 'index.html'));
  await page.evaluate(() => window.__ready);
  const stage = await page.$('#stage');

  const stillsArg = process.argv.indexOf('--stills');
  if (stillsArg > -1) {
    for (const t of process.argv[stillsArg + 1].split(',').map(Number)) {
      await page.evaluate(t => window.render(t), t);
      await stage.screenshot({ path: path.join(outDir, `still_${t}.png`) });
    }
    await browser.close();
    return;
  }

  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', path.join(outDir, 'frames.mp4')],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  const total = FPS * DUR;
  for (let f = 0; f < total; f++) {
    await page.evaluate(t => window.render(t), f / FPS);
    const buf = await stage.screenshot({ type: 'png' });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (f % 90 === 0) console.log(`frame ${f}/${total}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();
  console.log('done');
})();
