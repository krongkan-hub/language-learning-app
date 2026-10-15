// Colours and the two colour operations the pixel kit is built on, ported
// from docs/design/pixel/kit.js unchanged (kit.test.ts holds them to it).

export const SKIN = { a: '#f2cfae', b: '#e2ad84', c: '#bf855a', d: '#8a5a3c', e: '#5e3a28' } as const
export const HAIRC = {
  brown: '#6e4328', black: '#2c2830', blond: '#d4a64c', ginger: '#b5552e',
  gray: '#9d9aa3', white: '#e6e2dc', auburn: '#7d3324',
} as const

export type Skin = keyof typeof SKIN
export type HairColor = keyof typeof HAIRC

function rgb(c: string): number[] {
  return [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16))
}

/** Darken (f < 1) towards black, or lighten (f > 1) towards white. */
export function sh(c: string, f: number): string {
  const [r, g, b] = rgb(c)
  const m = (v: number) => Math.max(0, Math.min(255, Math.round(f > 1 ? v + (255 - v) * (f - 1) : v * f)))
  return '#' + [m(r), m(g), m(b)].map((v) => v.toString(16).padStart(2, '0')).join('')
}

export function mix(a: string, b: string, t: number): string {
  const A = rgb(a), B = rgb(b)
  return '#' + A.map((v, i) => Math.round(v + (B[i] - v) * t).toString(16).padStart(2, '0')).join('')
}
