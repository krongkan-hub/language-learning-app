// The café: docs/design/pixel/scene-cafe.js, ported statement for statement
// (only types added). Drawn by the character kit's rules: colour outlines,
// light from the top-left, three-tone shading, real textures, and the
// speaker's shadow on the wall. 208x112 logical pixels; `who` is a bust
// painted by render.ts, `t` the animation tick (steam).
import { sh } from './palettes'

export const CAFE_W = 208, CAFE_H = 112

export function drawCafe(c: CanvasRenderingContext2D, who: HTMLCanvasElement | null, t = 0): void {
  const W = 208, H = 112;
  const R = (x: number, y: number, w: number, h: number, col: string) => { c.fillStyle = col; c.fillRect(x, y, w, h) };
  const px = (x: number, y: number, col: string) => { c.fillStyle = col; c.fillRect(x, y, 1, 1) };
  const hash = (x: number, y: number) => (((x * 73856093) ^ (y * 19349663) ^ (x * y * 83492791)) >>> 0) % 100;
  const shade = (col: string, f: number) => sh(col, f);
  // a shaded block with a colour outline (light from the top-left)
  function obj(x: number, y: number, w: number, h: number, base: string, o: { mid?: boolean; noOutline?: boolean } = {}) {
    R(x, y, w, h, base);
    R(x, y, w, 1, shade(base, 1.2)); R(x, y + 1, 1, h - 1, shade(base, 1.08));
    R(x + w - 1, y + 1, 1, h - 1, shade(base, .78)); R(x + 1, y + h - 1, w - 1, 1, shade(base, .74));
    if (o.mid) R(x + w - 3, y + 1, 2, h - 2, shade(base, .9));
    if (!o.noOutline) { const ol = shade(base, .48); R(x - 1, y, 1, h, ol); R(x + w, y, 1, h, ol); R(x, y - 1, w, 1, ol); R(x, y + h, w, 1, ol) }
  }
  function sprite(rows: string[], pal: Record<string, string>, ox: number, oy: number) { rows.forEach((r, y) => [...r].forEach((ch, x) => { if (ch !== '.' && pal[ch]) px(ox + x, oy + y, pal[ch]) })) }

  // ---------- wall: warm plaster with texture ----------
  const plaster = '#ead7b2';
  for (let y = 0; y < 62; y++) for (let x = 0; x < W; x++) {
    const h = hash(x, y); let v = plaster;
    if (h < 5) v = shade(plaster, .94); else if (h > 96) v = shade(plaster, 1.04);
    if (y > 54) v = shade(v, .96); // soft shade above the wainscot
    px(x, y, v);
  }
  // crown moulding
  R(0, 0, W, 3, '#8f5e36'); R(0, 0, W, 1, '#b8834f'); R(0, 3, W, 1, '#5e3a1e');
  // ---------- window with the street outside ----------
  const wx = 142, wy = 7, ww = 58, wh = 44;
  obj(wx - 3, wy - 3, ww + 6, wh + 6, '#8f5e36');
  for (let y = 0; y < wh; y++) for (let x = 0; x < ww; x++) { // sky, ordered dither between two blues
    const t2 = y / wh; const d = ((x + y) % 2) * .5;
    px(wx + x, wy + y, t2 + d * .25 < .45 ? '#8ec8ec' : '#b5dcf2');
  }
  // clouds
  sprite(['...wwww....', '.wwwwwwww..', 'wwwwwwwwwww', '.lllllllll.'], { w: '#ffffff', l: '#dbeef9' }, wx + 6, wy + 5);
  // buildings across the street
  obj(wx + 2, wy + 20, 16, 24, '#c98d62', { noOutline: true });
  for (let i = 0; i < 3; i++) for (let j = 0; j < 2; j++) R(wx + 4 + j * 7, wy + 23 + i * 7, 4, 4, '#5b6f86');
  obj(wx + 20, wy + 26, 14, 18, '#9fb1b8', { noOutline: true });
  for (let i = 0; i < 2; i++) R(wx + 23, wy + 29 + i * 7, 8, 3, '#41566a');
  // tree
  sprite(['....gggg.....', '..ggGGggg....', '.gGGGgggdg...', 'gGGgggggddg..', 'gggggdgggddg.', '.ggddgggddd..', '..gddddddd...', '.....bb......', '.....bb......', '.....bb......'],
    { g: '#5d9b4f', G: '#8cc46a', d: '#3f6e3c', b: '#6b4a2f' }, wx + 38, wy + 20);
  R(wx, wy + wh - 4, ww, 4, '#8b8f94'); R(wx, wy + wh - 4, ww, 1, '#a9aeb3');
  // mullions + glass glints
  R(wx + ww / 2 - 1, wy, 2, wh, '#6e4826'); R(wx, wy + 22, ww, 2, '#6e4826');
  for (let i = 0; i < 5; i++) { px(wx + 4 + i, wy + 14 - i, '#ffffffaa'); px(wx + 34 + i, wy + 40 - i, '#ffffffaa') }
  // sill + plant
  obj(wx - 5, wy + wh + 3, ww + 10, 3, '#a8744a');
  obj(wx + 44, wy + wh - 5, 9, 8, '#b5643f');
  sprite(['..g...g..', '.gGg.gGg.', 'gGggGggGg', '.ggGgggg.', '..ggggg..'], { g: '#4d8a4b', G: '#86c06a' }, wx + 44, wy + wh - 10);
  // light falling from the window: dithered wedge on the wall
  for (let y = wy + wh + 6; y < 62; y++) for (let x = 0; x < W; x++) {
    const a = x - (wx - 30) + (y - (wy + wh)) * 1.2, b = (wx + ww - 10) - x + (y - (wy + wh)) * .2;
    if (a > 0 && b > 0 && (x + y) % 2 === 0) px(x, y, shade(plaster, 1.05));
  }

  // ---------- framed poster ----------
  obj(8, 8, 22, 28, '#3a2b24');
  R(10, 10, 18, 24, '#efe2c4');
  sprite(['....s.s....', '...s.s.....', '.ooooooo...', '.offffffoo.', '.offffffo.o', '.offffffoo.', '..offffo...', '...oooo....', 'ppppppppppp'],
    { s: '#c9c1b0', o: '#5e3a1e', f: '#8f5e36', p: '#b8382c' }, 13, 14);
  R(12, 28, 14, 1, '#8f5e36'); R(13, 30, 10, 1, '#c9a979');

  // ---------- chalkboard menu ----------
  obj(72, 7, 52, 36, '#6e4826');
  for (let y = 9; y < 41; y++) for (let x = 74; x < 122; x++) px(x, y, hash(x, y) < 8 ? '#3a4a44' : '#2f3d38');
  const chalk = '#e9ece4', chalkD = '#b9c2bb';
  // "MENU" in 3x5 chalk letters
  const G: Record<string, string[]> = { M: ['101', '111', '111', '101', '101'], E: ['111', '100', '110', '100', '111'], N: ['101', '111', '111', '111', '101'], U: ['101', '101', '101', '101', '111'] };
  let lx = 88; for (const ch of 'MENU') { G[ch].forEach((r, yy) => [...r].forEach((p, xx) => { if (p === '1') px(lx + xx, 11 + yy, chalk) })); lx += 5 }
  for (let i = 0; i < 4; i++) { const y = 19 + i * 5; R(77, y, 18 + (i * 7) % 9, 1, chalkD); for (let x = 99; x < 112; x += 2) px(x, y, '#5f6e66'); R(113, y, 6, 1, '#f2c35b') }
  sprite(['.c.c.', 'ccccc', 'c...cc', 'c...c.', '.ccc.'], { c: chalk }, 110, 34);
  R(76, 41, 44, 2, '#8f5e36'); px(80, 41, chalk); px(81, 41, chalk);

  // ---------- pendant lamps with glow ----------
  for (const x of [58, 132]) {
    R(x, 0, 1, 10, '#3a2b24');
    for (let r = 1; r <= 12; r++) for (let a = 0; a < 40; a++) {
      const gx = Math.round(x + Math.cos(a / 40 * 6.283) * r * 1.5), gy = Math.round(16 + Math.abs(Math.sin(a / 40 * 6.283)) * r);
      if (gy > 14 && gy < 62 && (gx + gy + r) % 3 === 0) px(gx, gy, shade(plaster, 1.07));
    }
    sprite(['...oooo...', '..oyyYYo..', '.oyyyYYyo.', 'oyyyyyyyyo', 'oddddddddo', '...wwww...'], { o: '#5e3a1e', y: '#d99a2b', Y: '#f2c35b', d: '#a5701a', w: '#fff3c4' }, x - 5, 10);
  }

  // ---------- shelf with mugs, jar, trailing plant ----------
  obj(4, 44, 60, 3, '#8f5e36');
  sprite(['oo', 'ob', 'o.'], { o: '#5e3a1e', b: '#8f5e36' }, 8, 47); sprite(['oo', 'bo', '.o'], { o: '#5e3a1e', b: '#8f5e36' }, 56, 47);
  const mug = (x: number, col: string) => {
    sprite(['oooooo..', 'oHccccoo', 'oHccccoco', 'occcccoco', 'occcccoo.', '.ooooo...'], { o: shade(col, .45), c: col, H: shade(col, 1.3) }, x, 37);
  };
  mug(7, '#d9573f'); mug(17, '#f4efe4'); mug(27, '#6f9fd0');
  // bean jar (glass + dithered beans)
  for (let y = 31; y < 44; y++) for (let x = 39; x < 47; x++) {
    const edge = x === 39 || x === 46 || y === 43;
    px(x, y, edge ? '#8aa1a8' : y < 34 ? '#d8e7ea' : (hash(x, y) % 3 === 0 ? '#5a3720' : '#7a4c2c'));
  }
  R(39, 30, 8, 1, '#5e3a1e'); px(40, 34, '#ffffff'); px(40, 35, '#ffffff');
  // trailing plant spilling off the shelf
  obj(50, 38, 9, 6, '#c27a52');
  sprite(['.gGg..gG', 'gGggGggg', '.g..gg.g', '.G...g..', '.g...G..', '.g...g..', '.G......', '.g......'], { g: '#4d8a4b', G: '#86c06a' }, 50, 34);
  sprite(['g.', 'Gg', '.g', 'gG', '.g', 'g.'], { g: '#4d8a4b', G: '#86c06a' }, 51, 44);

  // ---------- wainscot: wood boards with grain ----------
  const wood = '#8f5e36';
  for (let y = 62; y < 80; y++) for (let x = 0; x < W; x++) {
    const board = Math.floor(x / 11); let v = wood;
    if ((y * 3 + board * 17 + (x % 11) * ((board % 3) + 1)) % 13 === 0) v = shade(wood, .86);
    if (x % 11 === 0) v = shade(wood, .62); else if (x % 11 === 1) v = shade(wood, 1.14);
    px(x, y, v);
  }
  R(0, 61, W, 1, '#5e3a1e'); R(0, 62, W, 1, '#b8834f');

  // ---------- the barista, with a soft shadow on the wall ----------
  if (who) {
    const tmp = document.createElement('canvas'); tmp.width = who.width; tmp.height = who.height;
    const tc = tmp.getContext('2d')!; tc.drawImage(who, 0, 0); tc.globalCompositeOperation = 'source-in'; tc.fillStyle = 'rgba(70,40,20,.22)'; tc.fillRect(0, 0, tmp.width, tmp.height);
    c.drawImage(tmp, 34 + 4, 34 + 1); c.drawImage(who, 34, 34);
  }

  // ---------- counter ----------
  for (let x = 0; x < W; x++) { // top: light wood with grain
    for (let y = 76; y < 81; y++) { let v = '#b8834f'; if ((x * 2 + y * 7) % 17 === 0) v = shade(v, .9); if (y === 76) v = '#d4a46e'; if (y === 80) v = shade('#b8834f', .7); px(x, y, v) }
  }
  R(0, 75, W, 1, '#5e3a1e');
  for (let y = 81; y < H; y++) for (let x = 0; x < W; x++) { // front panels
    const p = Math.floor(x / 26), lx2 = x % 26; let v = '#7e5130';
    if (lx2 === 0) v = '#4a2d18'; else if (lx2 === 1) v = '#9a6a3e';
    else if (lx2 > 3 && lx2 < 23 && y > 84 && y < 107) { v = '#6e4626'; if (lx2 === 4 || y === 85) v = '#4f311a'; if (lx2 === 22 || y === 106) v = '#8f5e36'; if ((y * 5 + p * 7 + lx2 * 2) % 19 === 0) v = shade(v, .9) }
    px(x, y, v);
  }
  R(0, 81, W, 1, '#3a2312');

  // ---------- pastry case ----------
  const cx0 = 84, cy0 = 61;
  obj(cx0, cy0, 40, 15, '#d4e9ee');
  for (let y = cy0 + 1; y < cy0 + 14; y++) for (let x = cx0 + 1; x < cx0 + 39; x++) if ((x - y) % 9 === 0) px(x, y, '#f4fbfc');
  R(cx0 + 1, cy0 + 9, 38, 1, '#a8c3c9');
  const croissant = ['..oooo..', '.oCccCo.', 'oCcCCcCo', 'occcccco', '.oooooo.'];
  [0, 9, 18].forEach(d => sprite(croissant, { o: '#7a4a1e', c: '#d68f3a', C: '#f0b45a' }, cx0 + 3 + d, cy0 + 3));
  const muffin = ['.mmmm.', 'mMmMmm', 'mmmmmm', 'pPpPpp', '.pppp.'];
  [0, 8].forEach(d => sprite(muffin, { m: '#6a3a24', M: '#8f5636', p: '#e9e2d2', P: '#ffffff' }, cx0 + 27 + d, cy0 + 9));
  R(cx0 + 6, cy0 + 10, 5, 2, '#f4efe4'); R(cx0 + 15, cy0 + 10, 5, 2, '#f4efe4');

  // ---------- espresso machine ----------
  const ex = 134, ey = 52;
  obj(ex, ey, 40, 24, '#a9b4bc', { mid: true });
  R(ex + 4, ey + 1, 2, 22, '#e3e9ec'); // chrome highlight stripe
  obj(ex + 2, ey - 6, 36, 5, '#7c868e'); // cup warmer
  [0, 7, 14, 21, 28].forEach(d => { obj(ex + 4 + d, ey - 10, 5, 4, '#f4efe4') });
  obj(ex + 8, ey + 10, 7, 6, '#4b5560'); obj(ex + 24, ey + 10, 7, 6, '#4b5560'); // group heads
  R(ex + 3, ey + 16, 14, 2, '#2a2e33'); R(ex + 23, ey + 16, 14, 2, '#2a2e33'); // portafilter handles
  sprite(['.ooo.', 'owwwo', 'owrwo', 'owwwo', '.ooo.'], { o: '#3a3f45', w: '#f4f4f4', r: '#b8382c' }, ex + 17, ey + 3); // gauge
  R(ex + 2, ey + 21, 36, 2, '#5d666e'); for (let x = ex + 3; x < ex + 37; x += 2) px(x, ey + 21, '#8a949c'); // drip tray
  R(ex + 38, ey + 6, 1, 12, '#c9d1d6'); px(ex + 38, ey + 18, '#8a949c'); // steam wand
  // steam puffs (animated)
  const st = t % 2 ? ['.w.', 'w..', '.w.', '..w'] : ['w..', '.w.', '..w', '.w.'];
  sprite(st, { w: '#ffffffcc' }, ex + 10, ey + 2 - 4); sprite(st, { w: '#ffffffcc' }, ex + 26, ey + 1 - 4);

  // ---------- grinder ----------
  obj(178, 60, 12, 16, '#3a3f45'); obj(177, 50, 14, 10, '#c6d6db');
  for (let y = 53; y < 59; y++) for (let x = 178; x < 190; x++) px(x, y, hash(x, y) % 3 ? '#6a3f22' : '#8a5634');
  R(179, 51, 3, 6, '#eef6f8');

  // ---------- small props on the counter ----------
  for (let y = 66; y < 76; y++) for (let x = 192; x < 200; x++) px(x, y, x === 192 || x === 199 || y === 75 ? '#8aa1a8' : y > 70 ? (hash(x, y) % 2 ? '#d9b04a' : '#7fae5f') : '#e3f0f2'); // tip jar with coins and notes
  R(192, 65, 8, 1, '#5e3a1e');
  obj(10, 66, 14, 10, '#33433b'); R(12, 68, 10, 1, '#e9ece4'); R(12, 71, 7, 1, '#b9c2bb'); // little menu stand
  for (const x of [118, 126]) { obj(x, 71, 6, 5, '#f4efe4'); R(x + 6, 72, 1, 2, '#c9c1b0') } // two cups waiting
  const st2 = t % 2 ? ['.w', 'w.', '.w'] : ['w.', '.w', 'w.'];
  sprite(st2, { w: '#ffffffcc' }, 119, 66); sprite(st2, { w: '#ffffffcc' }, 127, 65);

  // ---------- gentle vignette ----------
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const dx = Math.min(x, W - 1 - x), dy = Math.min(y, H - 1 - y);
    if ((dx < 3 || dy < 2) && (x + y) % 2 === 0) { c.fillStyle = 'rgba(40,20,10,.18)'; c.fillRect(x, y, 1, 1) }
  }
}
