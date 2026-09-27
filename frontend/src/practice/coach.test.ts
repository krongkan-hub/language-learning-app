import { describe, expect, it } from 'vitest'
import { fill, parseCorrections, parseLevelUp } from './coach'

describe('parseCorrections', () => {
  const text = '💡 Feedback:\n- ❌ "two bottle" → ✅ "two bottles" (after a number, use the plural)\n- ❌ "I go" → ✅ "I went"'

  it('splits each bullet into what was written, the fix and why', () => {
    expect(parseCorrections(text)).toEqual([
      { was: 'two bottle', now: 'two bottles', why: 'after a number, use the plural', repeats: undefined },
      { was: 'I go', now: 'I went', why: '', repeats: undefined },
    ])
  })

  it('marks a correction the learner has made before, matched by the quoted text', () => {
    const [first, second] = parseCorrections(text, [{ quoted: 'I go', occurrences: 3 }])
    expect(first.repeats).toBeUndefined()
    expect(second.repeats).toBe(3)
  })

  it('returns nothing for a line it cannot read, so the raw text is shown instead', () => {
    expect(parseCorrections('something → else')).toEqual([])
  })
})

describe('parseLevelUp', () => {
  it('finds the advisory rewrite only when the text says Level up', () => {
    expect(parseLevelUp('Perfectly natural!\nLevel up: "I want" → "I would like" (more polite)'))
      .toEqual({ to: 'I would like', why: 'more polite' })
    expect(parseLevelUp('"a" → "b"')).toBeNull()
  })
})

describe('fill', () => {
  it('fills known placeholders and leaves unknown ones visible', () => {
    expect(fill('{word} {n}/3 {x}', { word: 'menu', n: 2 })).toBe('menu 2/3 {x}')
    expect(fill(undefined, {})).toBe('')
  })
})
