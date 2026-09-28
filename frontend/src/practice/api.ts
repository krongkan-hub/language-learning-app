// Thin typed wrappers over the practice endpoints (app/web/routes.py).
import type { EndResult, Language, Mode, ScenarioCard, SessionHeader, Snapshot, Stats, Strings } from './types'

async function json<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(await problem(r))
  return r.json() as Promise<T>
}

/** FastAPI's {"detail": "..."} as a sentence; the raw body otherwise. */
export async function problem(r: Response): Promise<string> {
  const body = await r.text().catch(() => '')
  try {
    const detail = (JSON.parse(body) as { detail?: unknown }).detail
    if (typeof detail === 'string') return detail
  } catch { /* not JSON */ }
  return body || `HTTP ${r.status}`
}

function post(url: string, body?: unknown): Promise<Response> {
  return fetch(url, {
    method: 'POST',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

export const fetchStrings = async (lang: Language) =>
  (await json<{ strings: Strings }>(await fetch(`/api/strings?language=${lang}`))).strings

export const fetchStats = async (lang: Language) =>
  json<Stats>(await fetch(`/api/stats?language=${lang}`))

export const fetchScenarios = async (lang: Language) =>
  (await json<{ scenarios: ScenarioCard[] }>(await fetch(`/api/scenarios?language=${lang}`))).scenarios

/** A scenario by name, a random draw (no name), or an explain topic. */
export async function createSession(lang: Language, mode: Mode, scenario?: string): Promise<SessionHeader> {
  const body = mode === 'explain' ? { language: lang, mode: 'explain' }
    : scenario ? { language: lang, scenario, tasks: 10 }
    : { language: lang, tasks: 10 }
  return json<SessionHeader>(await post('/api/session', body))
}

/** null when the server no longer has it (restarted, or ended). */
export async function fetchSnapshot(sid: string): Promise<Snapshot | null> {
  try {
    const r = await fetch(`/api/session/${sid}`)
    return r.ok ? ((await r.json()) as Snapshot) : null
  } catch {
    return null
  }
}

export const postTurn = (sid: string, text: string) => post(`/api/turn/${sid}`, { text })
export const postSkip = (sid: string) => post(`/api/skip/${sid}`)

export async function postDrill(sid: string, text: string) {
  return json<{ correct: boolean; remaining: number; target?: string }>(await post(`/api/drill/${sid}`, { text }))
}

export async function endSession(sid: string): Promise<EndResult | null> {
  const r = await post(`/api/session/${sid}/end`)
  return r.ok ? ((await r.json()) as EndResult) : null
}
