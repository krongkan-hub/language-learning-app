import { describe, expect, it } from 'vitest'
import fixtures from './kit.fixtures.json'
import { renderKit, type KitSpec } from './render'

// The port against the approved kit, pixel for pixel (#62). The fixtures are
// what docs/design/pixel/kit.js itself drew, run in node by
// frontend/scripts/kit-fixtures.mjs: the barista in all six moods, the
// twelve example characters, and every hair, hat, head, outfit, skin, hair
// colour and extra on pixel-kit.html.

type Fixture = { spec: KitSpec; w: number; h: number; palette: string[]; rows: string[] }

function decode(f: Fixture): (string | null)[] {
  return f.rows.flatMap((r) => Array.from({ length: f.w }, (_, x) => {
    const cell = r.slice(2 * x, 2 * x + 2)
    return cell === '..' ? null : f.palette[parseInt(cell, 36)]
  }))
}

describe('the pixel kit port', () => {
  const all = Object.entries(fixtures as Record<string, Fixture>)

  it('covers the whole approved kit', () => {
    expect(all.length).toBe(60)
  })

  it.each(all)('draws %s exactly as kit.js does', (_, f) => {
    const got = renderKit(f.spec)
    expect([got.w, got.h]).toEqual([f.w, f.h])
    const want = decode(f)
    const moved = got.px.flatMap((v, i) => (v === want[i] ? [] : [`(${i % f.w},${Math.floor(i / f.w)}) ${v} != ${want[i]}`]))
    expect(moved).toEqual([])
  })
})
