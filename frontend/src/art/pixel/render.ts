// The pixel character renderer: docs/design/pixel/kit.js `compose` and `draw`,
// ported step for step. renderKit() is pure (a grid of colours, no canvas),
// so kit.test.ts can compare it with the original pixel for pixel in jsdom;
// paint() puts the grid on a canvas.
//
// Rules (P's sign-off, #62): outlines are a darker shade of each part's own
// colour, never black; light from the top-left; three-tone shading.
import { HANDFACES, type Mood } from './faces'
import { BODY, HAIRS, HEADS, Ht, TAPE, Wd, outfit } from './parts'
import { HAIRC, SKIN, mix, sh, type HairColor, type Skin } from './palettes'

export interface KitSpec {
  head?: 'oval' | 'square' | 'round'
  hair: string
  hairColor: HairColor
  skin: Skin
  outfit: string
  cloth: string          // the outfit's main colour
  accent?: string        // apron
  badge?: string         // badge, number patch, stripes
  hatColor?: string
  tie?: string
  iris?: string
  mood?: Mood
  beard?: boolean
  mustache?: boolean
  stubble?: boolean
  glasses?: boolean
  old?: boolean          // wrinkles
  tape?: boolean         // a tailor's measuring tape (added for the catalogue)
}

/** A rendered bust: `px[y * w + x]` is a colour, or null where it is clear. */
export interface Pixels {
  w: number
  h: number
  px: (string | null)[]
}

type Grid = string[][]

function compose(ch: KitSpec): Grid {
  const g: Grid = Array.from({ length: Ht }, () => Array(Wd).fill('.'))
  const lay = (rows: string[]) => rows.forEach((r, y) => [...(r || '')].forEach((c, x) => { if (c !== '.') g[y][x] = c }))
  lay(BODY); lay(outfit(ch.outfit))
  if (ch.tape) for (const [y, x] of TAPE) g[y][x] = 'Y'
  lay(HEADS[ch.head || 'oval'])
  for (const y of [9, 10]) { g[y][4] = 'S'; g[y][19] = 'S' }
  lay(HAIRS[ch.hair])
  if (ch.beard) {
    for (let y = 11; y <= 16; y++) for (let x = 5; x < 19; x++) {
      if (g[y][x] === 'S' && (y >= 13 || x < 8 || x > 15)) g[y][x] = 'Hf'
    }
  }
  return g
}

// kit.js calls region() on cells off the grid too; undefined is cloth there.
const region = (k: string | undefined) =>
  k === 'S' ? 'S' : (k === 'H' || k === 'Hf') ? 'H' : k !== undefined && 'NYK'.includes(k) ? 'N' : k === '.' ? '.' : 'C'

export function renderKit(ch: KitSpec): Pixels {
  const lo = compose(ch)
  const SC = 0.75, W4 = Wd * 2, H4 = Ht * 2, W2 = Math.round(W4 * SC), H2 = Math.round(H4 * SC)
  const w = W2 + 2, h = H2 + 2
  const out: (string | null)[] = Array(w * h).fill(null)
  const fill = (x: number, y: number, v: string) => { if (x >= 0 && y >= 0 && x < w && y < h) out[y * w + x] = v }

  // EPX / Scale2x on the part labels: diagonals become smooth curves instead of 2x2 stairs
  const L = (x: number, y: number) => (lo[y] || [])[x] || '.'
  const g48: Grid = Array.from({ length: H4 }, () => Array(W4).fill('.'))
  for (let y = 0; y < Ht; y++) for (let x = 0; x < Wd; x++) {
    const P0 = L(x, y), A = L(x, y - 1), B = L(x + 1, y), C = L(x - 1, y), D = L(x, y + 1)
    let e1 = P0, e2 = P0, e3 = P0, e4 = P0
    if (C === A && C !== D && A !== B) e1 = A
    if (A === B && A !== C && B !== D) e2 = B
    if (D === C && D !== B && C !== A) e3 = C
    if (B === D && B !== A && D !== C) e4 = D
    g48[2 * y][2 * x] = e1; g48[2 * y][2 * x + 1] = e2; g48[2 * y + 1][2 * x] = e3; g48[2 * y + 1][2 * x + 1] = e4
  }
  const g: Grid = Array.from({ length: H2 }, (_, y) => Array.from({ length: W2 }, (_, x) =>
    g48[Math.min(H4 - 1, Math.round(y / SC))][Math.min(W4 - 1, Math.round(x / SC))]))
  const S = SKIN[ch.skin], Hc = HAIRC[ch.hairColor]
  const col: Record<string, string> = {
    S, H: Hc, Hf: sh(Hc, .92), C: ch.cloth, c: '#efece4', A: ch.accent || '#b8834a', D: sh(ch.cloth, .74),
    N: ch.hatColor || '#2f3f6b', Y: ch.badge || '#e2b64a', K: sh(ch.hatColor || '#2f3f6b', .62), R: ch.tie || '#b23a48', B: '#7da2d6',
  }
  const buf: (string | null)[][] = Array.from({ length: H2 }, () => Array(W2).fill(null))
  const inR = (x: number, y: number, r: string) => x >= 0 && y >= 0 && x < W2 && y < H2 && region(g[y][x]) === r

  // 1) base + 3-tone volume shading (light from top-left)
  for (let y = 0; y < H2; y++) for (let x = 0; x < W2; x++) {
    const k = g[y][x]; if (k === '.') continue
    const r = region(k); let v = col[k] || col.C
    let dr = 0; while (dr < 5 && inR(x + dr + 1, y, r) && inR(x, y + dr + 1, r)) dr++
    let dl = 0; while (dl < 3 && inR(x - dl - 1, y, r) && inR(x, y - dl - 1, r)) dl++
    if (r === 'S') { // skin: one soft step, only on the shadow side of the face, so the jaw never reads as stubble
      let hr = 0; while (hr < 3 && inR(x + hr + 1, y, r)) hr++
      if (hr <= 1 && x > W2 / 2) v = sh(v, .92)
    } else if (dr <= 0) v = sh(v, .76)
    else if (dr <= 2) v = sh(v, .88)
    else if (dl === 0) v = sh(v, 1.14)
    if (r === 'H') { // strands + shine band
      if ((x * 2 + y) % 9 === 0) v = sh(v, .84)
      if ((x + y * 3) % 11 === 0) v = sh(v, 1.12)
      let top = 0; while (top < 6 && inR(x, y - top - 1, 'H')) top++
      if (top >= 2 && top <= 3 && x < W2 / 2 + 4 && k === 'H') v = mix(v, '#ffffff', .22)
    }
    if (r === 'C' && k === 'C') { // cloth folds
      if ((x - y) % 13 === 0 && y > H2 * 0.75) v = sh(v, .86)
      if ((x + y) % 17 === 0 && y > H2 * 0.8) v = sh(v, .9)
    }
    buf[y][x] = v
  }
  const P = (x: number, y: number, v: string) => { if (x >= 0 && y >= 0 && x < W2 && y < H2) buf[y][x] = v }
  const skin = (x: number, y: number, f: number) => { if (region(g[y]?.[x]) === 'S') P(x, y, sh(S, f)) }
  // 2) under-hair and under-chin shadows
  for (let y = 1; y < H2; y++) for (let x = 0; x < W2; x++) {
    if (g[y][x] === 'S' && region(g[y - 1][x]) === 'H') P(x, y, sh(S, .9))
    if (g[y][x] === 'S' && y >= 2 && g[y - 2][x] === 'S' && region(g[y - 2]?.[x]) === 'S'
        && y >= Math.round(30 * SC) && y < Math.round(36 * SC)) P(x, y, sh(S, .8))
  }
  const Q = (x: number, y: number, v: string) => P(Math.round(x * SC), Math.round(y * SC), v)
  const skinQ = (x: number, y: number, f: number) => skin(Math.round(x * SC), Math.round(y * SC), f)
  // ear inner
  ;[[9, 19], [9, 20], [38, 19], [38, 20]].forEach(([x, y]) => skinQ(x, y, .78))
  // 3) face: hand-drawn per mood at the final resolution (origin x9,y10; 20x13). Only paints over skin.
  const lash = mix(sh(Hc, .55), '#5a3a30', .4), iris = ch.iris || '#5b7a9a'
  const lipC = mix(sh(S, .8), '#c25f5f', .4)
  const FP: Record<string, string> = {
    b: sh(Hc, .8), B: sh(Hc, .94), l: lash, w: '#f4f1ea', i: mix(iris, '#2a2230', .45), I: mix(iris, '#ffffff', .1), h: '#ffffff',
    e: sh(S, .93), s: sh(S, .93), n: sh(S, .9), N: sh(S, .8), H: sh(S, 1.06), m: lipC, M: sh(lipC, .75),
    p: mix(S, '#c8706a', .3), t: '#f6f1e6', o: '#7a3a3a', c: mix(S, '#e88a7a', .16),
  }
  const rows = HANDFACES[ch.mood || 'neutral'] || HANDFACES.neutral
  rows.forEach((r, dy) => [...r].forEach((k, dx) => {
    const x = 9 + dx, y = 10 + dy
    if (k === '.' || !FP[k]) return
    if (region(g[y]?.[x]) !== 'S') return
    P(x, y, FP[k])
  }))
  if (ch.old) {
    ;[[19, 10], [20, 10], [21, 10], [26, 10], [27, 10], [28, 10], [14, 17], [14, 18], [33, 17], [33, 18], [20, 23], [20, 24], [27, 23], [27, 24]]
      .forEach(([x, y]) => skinQ(x, y, .8))
  }
  if (ch.mustache) { for (let x = 19; x <= 28; x++) { Q(x, 24, sh(Hc, .9)); if (x > 19 && x < 28) Q(x, 25, sh(Hc, x % 2 ? .8 : .95)) } }
  if (ch.stubble) {
    for (let y = 24; y <= 32; y++) for (let x = 12; x < 36; x++) {
      if (region(g[Math.round(y * SC)]?.[Math.round(x * SC)]) === 'S' && (x * 3 + y * 5) % 4 === 0 && !(y >= 25 && y <= 28 && x >= 19 && x <= 28)) skinQ(x, y, .84)
    }
  }
  if (ch.beard) {
    for (let y = 22; y < 36; y++) for (let x = 8; x < 40; x++) {
      if (region(g[Math.round(y * SC)]?.[Math.round(x * SC)]) === 'H' && (x + y * 2) % 5 === 0) Q(x, y, sh(Hc, .78))
    }
  }
  if (ch.glasses) {
    const fr = '#3e3848'
    for (const ex of [15, 27]) {
      for (let i = 0; i < 6; i++) { Q(ex + i, 15, fr); Q(ex + i, 19, fr) }
      for (let y = 15; y <= 19; y++) { Q(ex, y, fr); Q(ex + 5, y, fr) }
    }
    Q(21, 16, fr); Q(22, 16, fr); Q(23, 16, fr); Q(24, 16, fr); Q(25, 16, fr); Q(26, 16, fr)
    for (const ex of [16, 28]) Q(ex, 16, mix(buf[Math.round(16 * SC)][Math.round(ex * SC)] || '#fff', '#ffffff', .5))
  }
  // 4) paint
  for (let y = 0; y < H2; y++) for (let x = 0; x < W2; x++) { const v = buf[y][x]; if (v) fill(x + 1, y + 1, v) }
  // 5) selective outline at hi-res
  const at = (x: number, y: number) => (g[y] || [])[x] || '.'
  for (let y = -1; y <= H2; y++) for (let x = -1; x <= W2; x++) {
    const k = at(x, y)
    const nb = [[1, 0], [-1, 0], [0, 1], [0, -1]].map(([a, b]) => at(x + a, y + b))
    if (k === '.') {
      const src = nb.find((n) => n !== '.')
      if (src) {
        const r = region(src)
        const base = r === 'S' ? S : r === 'H' ? Hc : r === 'N' ? col.N : (col[src] || col.C)
        fill(x + 1, y + 1, sh(base, r === 'S' ? .62 : .48))
      }
    } else if (region(k) === 'H' && nb.some((n) => region(n) === 'S')) fill(x + 1, y + 1, sh(Hc, .68))
    else if (region(k) === 'S' && nb.some((n) => region(n) === 'C') && y >= Math.round(34 * SC)) fill(x + 1, y + 1, sh(S, .72))
  }
  return { w, h, px: out }
}

/** Paint a rendered bust onto `canvas`, sized to it (38x44 device pixels). */
export function paint(canvas: HTMLCanvasElement, p: Pixels): void {
  canvas.width = p.w; canvas.height = p.h
  const c = canvas.getContext('2d')
  if (!c) return
  const img = c.createImageData(p.w, p.h)
  p.px.forEach((v, i) => {
    if (!v) return
    img.data[i * 4] = parseInt(v.slice(1, 3), 16)
    img.data[i * 4 + 1] = parseInt(v.slice(3, 5), 16)
    img.data[i * 4 + 2] = parseInt(v.slice(5, 7), 16)
    img.data[i * 4 + 3] = 255
  })
  c.putImageData(img, 0, 0)
}
