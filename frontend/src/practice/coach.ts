// The coach panel is the reason this UI exists, and it used to show the raw
// text — `- ❌ "two bottle" → ✅ "two bottles" (after a number, use the
// plural)` — as one run-on line. The learner has to be able to see at a glance
// what they wrote, what it should be, and why. Pure functions: tested in
// coach.test.ts without rendering anything.
import type { Repeat } from './types'

export interface Correction {
  was: string
  now: string
  why: string
  repeats?: number // how often this learner has made it before (db.repeats_among)
}

export interface LevelUp {
  to: string
  why: string
}

export function parseCorrections(text: string, repeats: Repeat[] = []): Correction[] {
  const out: Correction[] = []
  for (const line of text.split('\n').filter((l) => l.includes('→'))) {
    const m = line.match(/❌\s*"(.*?)"\s*→\s*✅\s*"(.*?)"\s*(?:\((.*)\))?/)
    if (!m) continue
    // matched by the quoted text the coach itself wrote
    const rep = repeats.find((r) => r.quoted === m[1])
    out.push({ was: m[1], now: m[2], why: m[3] || '', repeats: rep?.occurrences })
  }
  return out
}

// A Level up is advisory — the drill never enforces it — so it is shown
// distinctly from a correction rather than in the same red/green as an error.
// A clean verdict often arrives with one attached.
export function parseLevelUp(text: string): LevelUp | null {
  const m = text.match(/"([^"]+)"\s*→\s*"([^"]+)"\s*(?:\((.*?)\))?/)
  if (!m || !/level up/i.test(text)) return null
  return { to: m[2], why: m[3] || '' }
}

/** Fills `{name}` placeholders from an i18n template; unknown ones stay as-is. */
export function fill(template: string | undefined, values: Record<string, string | number>): string {
  return (template || '').replace(/\{(\w+)\}/g, (m, k: string) => (k in values ? String(values[k]) : m))
}
