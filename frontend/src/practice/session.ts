// A running session as data: every server event (app/web/turns.py) and every
// learner action goes through `reduce`, a pure function — so the rules the
// old page kept in a 120-line `handle(ev)` are unit-tested in session.test.ts
// without a browser. Side effects (focus, scrolling, timers) live in the
// components that render this state.
import { copyFor } from './copy'
import { fill } from './coach'
import type { Language, Mode, Progress, Repeat, ServerEvent, SessionHeader, Snapshot, Strings, Task } from './types'

export type LogItem =
  | { id: number; kind: 'turn'; who: string; text: string; cls: 'npc' | 'you' | 'note' | 'note learned' }
  | { id: number; kind: 'vocab'; word: string; explanation: string }
  | { id: number; kind: 'error'; title: string; message: string; detail: string }

export interface Summary {
  done: number
  outOf: number
  missed: number
  progress?: Progress
  wordsDue?: number
}

export interface Notice {
  id: number
  text: string
}

export interface SessionState {
  lang: Language
  str: Strings
  sid: string | null
  mode: Mode
  header: { scenario: string; place: string; speaker: string; mood: string; total: number }
  log: LogItem[]
  streamingId: number | null // the NPC line 'sentence' events are growing
  announce: string // the screen-reader live region: one line per finished NPC turn
  tasks: Task[]
  lastDone: number
  justDone: number | null // index of the task that just completed, for the pop
  coach: { text: string; clean: boolean; repeats: Repeat[] } | null
  words: string[]
  drill: { target: string; remaining: number; msg: string } | null
  open: boolean // the input box accepts a turn
  thinking: boolean
  thinkingLabel: string
  boot: 'preparing' | 'greeting' | null
  summary: Summary | null
  // The stream drops when a session ends normally too; only a session that
  // died on its own should be told to reload (see useEventStream).
  endedOnPurpose: boolean
  retriedNote: string
  banner: { text: string; fatal: boolean; id: number } | null
  toasts: Notice[]
  nextId: number
}

export function initialState(lang: Language = 'English'): SessionState {
  return {
    lang, str: {}, sid: null, mode: 'scenario',
    header: { scenario: '—', place: '', speaker: '', mood: '', total: 0 },
    log: [], streamingId: null, announce: '',
    tasks: [], lastDone: 0, justDone: null,
    coach: null, words: [], drill: null,
    open: false, thinking: false, thinkingLabel: copyFor(lang).thinking,
    boot: null, summary: null, endedOnPurpose: false, retriedNote: '',
    banner: null, toasts: [], nextId: 1,
  }
}

export type Action =
  | { type: 'strings'; lang: Language; str: Strings }
  | { type: 'booting' }
  | { type: 'started'; header: SessionHeader }
  | { type: 'resumed'; snap: Snapshot }
  | { type: 'event'; ev: ServerEvent }
  | { type: 'sent'; text: string }
  | { type: 'drillResult'; correct: boolean; remaining: number; target?: string }
  | { type: 'ended'; summary: Summary }
  | { type: 'reviewing' }
  | { type: 'streamLost'; fatal: boolean }
  | { type: 'banner'; text: string; fatal?: boolean }
  | { type: 'dismissBanner'; id: number }
  | { type: 'toast'; text: string }
  | { type: 'dismissToast'; id: number }

function withHeader(s: SessionState, h: SessionHeader): SessionState {
  return {
    ...s, sid: h.session, mode: h.mode || 'scenario',
    header: { scenario: h.scenario, place: h.place, speaker: h.speaker,
              // already trimmed to its first clause and localized by the server
              mood: h.mood ? '· ' + h.mood : '', total: h.total_tasks },
    retriedNote: h.retried_note || '',
  }
}

function append(s: SessionState, item: DistributiveOmit<LogItem, 'id'>): SessionState {
  return { ...s, log: [...s.log, { ...item, id: s.nextId } as LogItem], nextId: s.nextId + 1 }
}

type DistributiveOmit<T, K extends keyof T> = T extends unknown ? Omit<T, K> : never

function toast(s: SessionState, text: string): SessionState {
  return { ...s, toasts: [...s.toasts, { id: s.nextId, text }], nextId: s.nextId + 1 }
}

function banner(s: SessionState, text: string, fatal = false): SessionState {
  return { ...s, banner: { text, fatal, id: s.nextId }, nextId: s.nextId + 1 }
}

function summarise(s: SessionState, summary: Summary): SessionState {
  return { ...s, summary, endedOnPurpose: true, open: false, thinking: false }
}

export function reduce(s: SessionState, a: Action): SessionState {
  const c = copyFor(s.lang)
  switch (a.type) {
    case 'strings':
      return { ...s, lang: a.lang, str: a.str, thinkingLabel: copyFor(a.lang).thinking }
    case 'booting':
      return { ...s, boot: 'preparing' }
    case 'started':
      // a fresh draw: nothing from the last session carries over
      return withHeader({ ...initialState(a.header.language), str: s.str, boot: s.boot, nextId: s.nextId }, a.header)
    case 'resumed': {
      const d = a.snap
      let next = withHeader({ ...initialState(d.language), str: s.str, nextId: s.nextId }, d)
      for (const m of d.messages) {
        next = append(next, m.role === 'assistant'
          ? { kind: 'turn', who: d.speaker, text: m.content, cls: 'npc' }
          : { kind: 'turn', who: 'You', text: m.content, cls: 'you' })
      }
      next = { ...next, words: [...d.words] }
      next = reduce(next, { type: 'event', ev: { type: 'tasks', tasks: d.tasks } })
      next = { ...next, justDone: null, toasts: [] }  // nothing "just" happened
      next = reduce(next, { type: 'event', ev: { type: 'state', state: d.state } })
      // The drill is a modal with no other way out, so a reload during one
      // has to put it back or the learner is stuck at a disabled input box.
      if (d.state === 'drill' && d.drill.length)
        next = reduce(next, { type: 'event', ev: { type: 'drill', target: d.drill[0], remaining: d.drill.length } })
      // A session that reached its last task stays on the server until /end,
      // so a reload can land on a finished one: show the summary, not a
      // transcript the learner cannot type into.
      if (d.state === 'finished')
        return summarise(next, { done: d.tasks_done, outOf: d.total_tasks, missed: d.tasks_missed,
                                 progress: d.progress, wordsDue: d.words_due })
      return banner(next, copyFor(d.language).resumed)
    }
    case 'sent':
      return { ...append(s, { kind: 'turn', who: 'You', text: a.text, cls: 'you' }), open: false, thinking: true }
    case 'drillResult':
      if (!s.drill) return s
      if (a.correct && a.remaining === 0) return { ...s, drill: null }
      if (a.correct) return { ...s, drill: { target: a.target ?? s.drill.target, remaining: a.remaining, msg: '' } }
      return { ...s, drill: { ...s.drill, msg: s.str.drill_retry || 'Not quite — type it exactly.' } }
    case 'ended':
      return summarise(s, a.summary)
    case 'reviewing':
      return { ...s, summary: null }
    case 'streamLost':
      if (!a.fatal) return banner(s, c.reconnecting)
      return { ...(s.endedOnPurpose ? s : banner(s, c.ended, true)), open: false, boot: null }
    case 'banner':
      // a fatal one (a session that could not start) also takes the loading screen down
      return a.fatal ? { ...banner(s, a.text, true), boot: null } : banner(s, a.text)
    case 'dismissBanner':
      return s.banner?.id === a.id ? { ...s, banner: null } : s
    case 'toast':
      return toast(s, a.text)
    case 'dismissToast':
      return { ...s, toasts: s.toasts.filter((t) => t.id !== a.id) }
    case 'event':
      return onEvent(s, a.ev)
  }
}

function onEvent(s: SessionState, ev: ServerEvent): SessionState {
  const c = copyFor(s.lang)
  switch (ev.type) {
    case 'sentence': {
      const cur = s.log.find((l) => l.id === s.streamingId)
      if (cur && cur.kind === 'turn') {
        const text = cur.text ? cur.text + ' ' + ev.text : ev.text
        return { ...s, boot: null, log: s.log.map((l) => (l.id === cur.id ? { ...cur, text } : l)) }
      }
      const next = append({ ...s, boot: null }, { kind: 'turn', who: s.header.speaker, text: ev.text, cls: 'npc' })
      return { ...next, streamingId: s.nextId }
    }
    case 'npc': {
      // When the reply streamed in, the log already holds it in full and
      // ev.text would duplicate it; when it did not, ev.text is the only copy.
      const streamed = s.log.find((l) => l.id === s.streamingId)
      let next: SessionState = { ...s, boot: null, streamingId: null }
      const full = streamed && streamed.kind === 'turn' ? streamed.text : ev.text
      if (!streamed) next = append(next, { kind: 'turn', who: s.header.speaker, text: ev.text, cls: 'npc' })
      next = { ...next, announce: `${s.header.speaker}: ${full}` }
      // context for the task list, shown once the scene is up — not over the loading screen
      if (s.retriedNote) next = { ...banner(next, s.retriedNote), retriedNote: '' }
      return next
    }
    case 'vocab': {
      // The card stays in the transcript on a repeat — the NPC did teach it
      // again — but the collected list and the word count must not double.
      const next = append(s, { kind: 'vocab', word: ev.word, explanation: ev.explanation })
      if (ev.repeat) return next
      return toast({ ...next, words: [...next.words, ev.word] }, c.newWord(ev.word))
    }
    case 'vocab_used': {
      // A taught word used in the learner's own sentence counts as practice;
      // three uses and it leaves the review list.
      let next = s
      for (const u of ev.words || []) {
        const learned = u.count >= 3
        const tmpl = learned
          ? s.str.web_vocab_learned || '★ “{word}” learned — used three times, off your review list'
          : s.str.web_vocab_used || '✓ You used “{word}” — {n}/3'
        next = append(next, { kind: 'turn', who: '', text: fill(tmpl, { word: u.word, n: u.count }),
                              cls: learned ? 'note learned' : 'note' })
      }
      return next
    }
    case 'coach':
      return { ...s, coach: { text: ev.text, clean: ev.clean, repeats: ev.repeats || [] } }
    case 'tasks': {
      const done = ev.tasks.filter((t) => t.done).length
      // Done ones are no longer a prefix once a task has been skipped, so the
      // newest is the last done index, not done-1.
      let lastIdx = -1
      ev.tasks.forEach((t, i) => { if (t.done) lastIdx = i })
      const advanced = lastIdx >= 0 && done > s.lastDone
      const next = { ...s, tasks: ev.tasks, lastDone: done, justDone: advanced ? lastIdx : null }
      return advanced ? toast(next, c.taskDone) : next
    }
    case 'drill':
      return { ...s, drill: { target: ev.target, remaining: ev.remaining, msg: '' } }
    case 'drill_done':
      return { ...s, drill: null }
    case 'task_result': {
      // Without these a task that ran out of attempts just turned into a ✗,
      // which reads as a skip nobody pressed.
      if (ev.done) return s
      let msg = ev.moved_on
        ? fill(s.str.moving_on_failed, { n: ev.attempts, goal: ev.goal ?? '' })
        : fill(s.str.task_not_completed, { n: ev.attempts, max: ev.max_attempts ?? '' })
      if (!ev.moved_on && ev.strategy) msg += '\n' + fill(s.str.strategy_hint, { hint: ev.strategy })
      if (!ev.moved_on && ev.hint) msg += '\n' + fill(s.str.judge_note, { hint: ev.hint })
      return append(s, { kind: 'turn', who: '', text: msg, cls: 'note' })
    }
    case 'stage':
      if (ev.name === 'preparing' || ev.name === 'greeting') return { ...s, boot: ev.name }
      return c.stage[ev.name] ? { ...s, thinkingLabel: c.stage[ev.name] } : s
    case 'finished':
      return summarise(s, { done: ev.tasks_done, outOf: ev.tasks_total || s.header.total,
                            missed: ev.tasks_missed, progress: ev.progress, wordsDue: ev.words_due })
    case 'error':
      // Not a chat turn: an error rendered as dialogue reads as if the NPC said it.
      return append({ ...s, boot: null }, { kind: 'error', title: c.couldntSend,
                                                     message: ev.message || '', detail: ev.detail || '' })
    case 'state': {
      const open = ev.state === 'awaiting_input'
      return { ...s, open, thinking: ev.state === 'busy' }
    }
    case 'closed':
      return s
  }
}

/** The line under the summary score: what is TRUE and earned, no invented points. */
export function whatsNext(lang: Language, progress?: Progress, wordsDue?: number): string {
  const c = copyFor(lang)
  const bits: string[] = []
  if (progress?.next_rank) {
    const rank = c.rank(progress.next_rank)
    if ((progress.plays_needed ?? 0) > 0) bits.push(c.playsTo(progress.plays_needed!, rank))
    else if ((progress.pct_needed ?? 0) > 0) bits.push(c.pctTo(progress.pct_needed!, rank))
  }
  if (wordsDue && wordsDue > 0) bits.push(c.wordsDue(wordsDue))
  return bits.join(c.sep)
}

/** Green is for having done well, not for having finished; zero is muted, not red. */
export function scoreClass(done: number, outOf: number): string {
  return 'big' + (!done ? ' none' : outOf && done >= outOf * 0.6 ? ' most' : '')
}
