// XP and level (#62): derived from what the app already stores, never graded.
// The one place the formula lives; xp.test.ts pins it.
//
//   XP    = 10 × tasks done + 20 × red marks fixed + 50 × mistakes retired
//   level n starts at 50·n·(n−1) XP: 0, 100, 300, 600, 1000… each level is
//   100 XP longer than the one before.
//
// The lifetime counts come from GET /api/today (`totals`, finished sessions
// only, app/db/mistakes.py game_totals); the session in progress adds its own
// tasks done and corrections retyped right. The streak is shown beside the
// level but earns no XP: it resets after a missed day, and XP never goes down.
import type { Today } from './api'
import type { SessionState } from './session'

export interface Totals {
  tasks_done: number
  fixes: number
  retired: number
}

export const XP_PER = { task: 10, fix: 20, retired: 50 } as const

export const NO_TOTALS: Totals = { tasks_done: 0, fixes: 0, retired: 0 }

export function xpOf(t: Totals): number {
  return t.tasks_done * XP_PER.task + t.fixes * XP_PER.fix + t.retired * XP_PER.retired
}

const levelStart = (n: number) => 50 * n * (n - 1)

/** The level `xp` reaches, and how far into it: `into` of `span` XP. */
export function levelOf(xp: number): { level: number; into: number; span: number } {
  let level = 1
  while (levelStart(level + 1) <= xp) level++
  return { level, into: xp - levelStart(level), span: levelStart(level + 1) - levelStart(level) }
}

/** What this session has earned so far: its tasks done (the server's count once it has ended) and its fixes. */
export function sessionTotals(s: SessionState): Totals {
  const done = s.summary ? s.summary.done : s.tasks.filter((t) => t.done).length
  return { tasks_done: done, fixes: s.hanamaru, retired: 0 }
}

export function plus(a: Totals, b: Totals): Totals {
  return { tasks_done: a.tasks_done + b.tasks_done, fixes: a.fixes + b.fixes, retired: a.retired + b.retired }
}

/** Lifetime totals from Today's data; zero while it loads. */
export const totalsOf = (today: Today | null): Totals => today?.totals ?? NO_TOTALS
