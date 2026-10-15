import { describe, expect, it } from 'vitest'
import { initialState, reduce } from './session'
import { levelOf, plus, sessionTotals, totalsOf, xpOf } from './xp'

describe('XP and level (#62)', () => {
  it('XP is 10 per task done, 20 per red mark fixed, 50 per mistake retired', () => {
    expect(xpOf({ tasks_done: 0, fixes: 0, retired: 0 })).toBe(0)
    expect(xpOf({ tasks_done: 3, fixes: 2, retired: 1 })).toBe(30 + 40 + 50)
  })

  it('each level is 100 XP longer than the one before', () => {
    expect(levelOf(0)).toEqual({ level: 1, into: 0, span: 100 })
    expect(levelOf(99)).toEqual({ level: 1, into: 99, span: 100 })
    expect(levelOf(100)).toEqual({ level: 2, into: 0, span: 200 })
    expect(levelOf(299)).toEqual({ level: 2, into: 199, span: 200 })
    expect(levelOf(300)).toEqual({ level: 3, into: 0, span: 300 })
    expect(levelOf(1000).level).toBe(5)
  })

  it('a session adds its tasks done and its corrections retyped, and the server count once it ends', () => {
    let s = initialState()
    s = reduce(s, { type: 'event', ev: { type: 'tasks', tasks: [
      { index: 0, goal: 'a', done: true, skipped: false, current: false },
      { index: 1, goal: 'b', done: false, skipped: true, current: false },
      { index: 2, goal: 'c', done: false, skipped: false, current: true }] } })
    s = { ...s, hanamaru: 2 }
    expect(sessionTotals(s)).toEqual({ tasks_done: 1, fixes: 2, retired: 0 })
    s = reduce(s, { type: 'ended', summary: { done: 2, outOf: 3, missed: 1 } })
    expect(sessionTotals(s).tasks_done).toBe(2)
  })

  it('lifetime totals are zero until Today has loaded, and add up with the session', () => {
    expect(totalsOf(null)).toEqual({ tasks_done: 0, fixes: 0, retired: 0 })
    const today = { review: [], recent: [], done_today: 0, streak: 0, totals: { tasks_done: 5, fixes: 4, retired: 1 } }
    expect(plus(totalsOf(today), { tasks_done: 1, fixes: 1, retired: 0 })).toEqual({ tasks_done: 6, fixes: 5, retired: 1 })
  })
})
