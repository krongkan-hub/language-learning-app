// Every line in copy.ts speaks one language: an English session never shows
// 花丸, a Japanese one never shows an English word (#67).
import { describe, expect, it } from 'vitest'
import { copyFor } from './copy'

const CJK = /[぀-ヿ㐀-鿿]/
const LATIN = /[A-Za-z]/

// Every visible line, with the functions called on sample arguments.
function lines(x: unknown, path = ''): [string, string][] {
  if (typeof x === 'string') return [[path, x]]
  if (typeof x === 'function') {
    const arg = path.endsWith('.date') ? new Date(2026, 9, 15) : path.endsWith('.rank') ? 'experienced' : 2
    return [[path, String(x(arg, 2))]]
  }
  if (Array.isArray(x)) return x.flatMap((v, i) => lines(v, `${path}[${i}]`))
  if (x && typeof x === 'object') {
    // htmlLang and reward.icon are keys for the page, never shown
    return Object.entries(x).filter(([k]) => k !== 'htmlLang' && k !== 'icon').flatMap(([k, v]) => lines(v, `${path}.${k}`))
  }
  return []
}

describe('copy follows the session language', () => {
  it('English has no Japanese in it', () => {
    expect(lines(copyFor('English')).filter(([, s]) => CJK.test(s))).toEqual([])
  })

  it('Japanese has no English in it', () => {
    expect(lines(copyFor('Japanese')).filter(([, s]) => LATIN.test(s))).toEqual([])
  })

  it('names the reward for the language: Gold Star in English, 花丸 in Japanese (#62)', () => {
    expect(copyFor('English').reward).toMatchObject({ icon: 'star', name: 'Gold Star' })
    expect(copyFor('Japanese').reward).toMatchObject({ icon: 'hanamaru', name: '花丸' })
    expect(lines(copyFor('English')).filter(([, s]) => /gold star/.test(s))).toEqual([])   // one spelling: Gold Star
  })

  it('says how a red mark leaves the redo: right in two separate redos, back if made again', () => {
    expect(copyFor('English').page.comeBack).toMatch(/two separate redos/)
    expect(copyFor('English').page.comeBack).not.toMatch(/until they stick/)
    expect(copyFor('Japanese').page.comeBack).toMatch(/別々の「やり直し」で2回/)
  })
})
