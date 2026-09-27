// Test double for the practice API and its event stream: enough of
// app/web/routes.py to drive the rendered page in jsdom.
import { act } from '@testing-library/react'
import { vi } from 'vitest'
import type { ServerEvent } from './types'

export class FakeEventSource {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 2
  static last: FakeEventSource | null = null
  readyState = FakeEventSource.OPEN
  onmessage: ((e: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  closed = false
  url: string
  constructor(url: string) {
    this.url = url
    FakeEventSource.last = this
  }
  close() { this.closed = true; this.readyState = FakeEventSource.CLOSED }
}

/** Deliver server events to the page, as the stream would. */
export function emit(...events: ServerEvent[]) {
  act(() => {
    for (const ev of events) FakeEventSource.last!.onmessage!({ data: JSON.stringify(ev) })
  })
}

type Route = (body: unknown) => unknown
export interface Call { method: string; url: string; body: unknown }

export const HEADER = {
  session: 's1', language: 'English', mode: 'scenario', scenario: 'Coffee Shop', place: 'A café',
  speaker: 'Barista', mood: 'cheerful', total_tasks: 3, retried_note: '',
}

/** Installs fetch + EventSource fakes; `routes` maps "METHOD /path" (no query) to a JSON body, or a status number. */
export function installServer(routes: Record<string, unknown | Route> = {}) {
  const calls: Call[] = []
  const table: Record<string, unknown | Route> = {
    'GET /api/strings': { strings: {} },
    'GET /api/stats': { overall: {}, vocab: {} },
    'GET /api/scenarios': { scenarios: [] },
    'POST /api/session': HEADER,
    'POST /api/turn/s1': {},
    ...routes,
  }
  vi.stubGlobal('EventSource', FakeEventSource)
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method || 'GET'
    const body = init?.body ? JSON.parse(String(init.body)) : undefined
    calls.push({ method, url, body })
    const hit = table[`${method} ${url.split('?')[0]}`]
    const value = typeof hit === 'function' ? (hit as Route)(body) : hit
    const status = hit === undefined ? 404 : typeof value === 'number' ? value : 200
    return {
      ok: status < 400, status,
      json: async () => value, text: async () => JSON.stringify(value ?? 'not found'),
    }
  }))
  return calls
}
