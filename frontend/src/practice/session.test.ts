import { describe, expect, it } from 'vitest'
import { initialState, reduce, scoreClass, whatsNext, type Action, type SessionState } from './session'
import type { ServerEvent, SessionHeader, Snapshot, Task } from './types'

const HEADER: SessionHeader = {
  session: 'abc', language: 'English', mode: 'scenario', scenario: 'Coffee Shop', place: 'A café',
  speaker: 'Barista', mood: 'cheerful', total_tasks: 3, retried_note: '',
}

function run(...actions: Action[]): SessionState {
  const start = reduce(initialState(), { type: 'started', header: HEADER })
  return actions.reduce(reduce, start)
}
const ev = (e: ServerEvent): Action => ({ type: 'event', ev: e })
const task = (goal: string, over: Partial<Task> = {}): Task =>
  ({ index: 0, goal, done: false, skipped: false, current: false, ...over })

describe('the NPC turn', () => {
  it('streams into one line and is announced once, without a duplicate', () => {
    const s = run(ev({ type: 'sentence', text: 'Hello.' }), ev({ type: 'sentence', text: 'Welcome in.' }),
                  ev({ type: 'npc', text: 'Hello. Welcome in.' }))
    expect(s.log).toHaveLength(1)
    expect(s.log[0]).toMatchObject({ kind: 'turn', who: 'Barista', text: 'Hello. Welcome in.', cls: 'npc' })
    expect(s.announce).toBe('Barista: Hello. Welcome in.')
    expect(s.streamingId).toBeNull()
  })

  it('keeps the whole reply when a reload cut the stream short', () => {
    const s = run(ev({ type: 'sentence', text: 'Only the end.' }),
                  ev({ type: 'npc', text: 'The start. Only the end.' }))
    expect(s.log).toHaveLength(1)
    expect(s.log[0]).toMatchObject({ text: 'The start. Only the end.' })
  })

  it('is added whole when it did not stream', () => {
    const s = run(ev({ type: 'npc', text: 'Hi.' }))
    expect(s.log.map((l) => l.kind === 'turn' && l.text)).toEqual(['Hi.'])
  })

  it('shows the retried-tasks note once the scene is up, then never again', () => {
    const start = reduce(initialState(), { type: 'started', header: { ...HEADER, retried_note: '2 tasks carried over' } })
    const s = [ev({ type: 'npc', text: 'Hi.' }), ev({ type: 'npc', text: 'Again.' })].reduce(reduce, start)
    expect(s.banner?.text).toBe('2 tasks carried over')
    expect(s.retriedNote).toBe('')
  })
})

describe('vocabulary', () => {
  it('keeps a repeated card in the transcript but does not collect the word twice', () => {
    const s = run(ev({ type: 'vocab', word: 'latte', explanation: 'coffee with milk' }),
                  ev({ type: 'vocab', word: 'latte', explanation: 'coffee with milk', repeat: true }))
    expect(s.log.filter((l) => l.kind === 'vocab')).toHaveLength(2)
    expect(s.words).toEqual(['latte'])
    expect(s.toasts).toHaveLength(1)
  })

  it('credits a word the learner used, from the served template', () => {
    const s = [{ type: 'strings', lang: 'English', str: { web_vocab_used: 'used {word} {n}/3', web_vocab_learned: 'learned {word}' } } as Action,
               ev({ type: 'vocab_used', words: [{ word: 'latte', count: 2 }, { word: 'menu', count: 3 }] })]
      .reduce(reduce, run())
    expect(s.log.map((l) => l.kind === 'turn' && [l.text, l.cls])).toEqual([
      ['used latte 2/3', 'note'], ['learned menu', 'note learned']])
  })
})

describe('tasks', () => {
  it('pops and toasts only the task that just completed, even after a skip', () => {
    let s = run(ev({ type: 'tasks', tasks: [task('a', { current: true }), task('b'), task('c')] }))
    expect(s.justDone).toBeNull()
    s = reduce(s, ev({ type: 'tasks', tasks: [task('a', { skipped: true }), task('b', { done: true }), task('c', { current: true })] }))
    expect(s.justDone).toBe(1)
    expect(s.toasts).toHaveLength(1)
    s = reduce(s, ev({ type: 'tasks', tasks: [task('a', { skipped: true }), task('b', { done: true }), task('c', { current: true })] }))
    expect(s.justDone).toBeNull()      // nothing new
    expect(s.toasts).toHaveLength(1)
  })

  it('tells the learner when a task ran out of attempts, from the served strings', () => {
    const str = { task_not_completed: 'not yet ({n}/{max})', strategy_hint: 'try: {hint}',
                  judge_note: 'note: {hint}', moving_on_failed: 'moving on after {n}: {goal}' }
    const base = reduce(run(), { type: 'strings', lang: 'English', str })
    const miss = reduce(base, ev({ type: 'task_result', done: false, attempts: 1, max_attempts: 3, strategy: 'ask', hint: 'close' }))
    expect(miss.log.at(-1)).toMatchObject({ text: 'not yet (1/3)\ntry: ask\nnote: close', cls: 'note' })
    const gave = reduce(base, ev({ type: 'task_result', done: false, moved_on: true, attempts: 3, goal: 'order' }))
    expect(gave.log.at(-1)).toMatchObject({ text: 'moving on after 3: order' })
    expect(reduce(base, ev({ type: 'task_result', done: true, attempts: 1 })).log).toHaveLength(0)
  })
})

describe('corrections', () => {
  it('are collected for the summary, once each, clean verdicts adding nothing', () => {
    const fix = '💡 Feedback:\n- ❌ "two bottle" → ✅ "two bottles" (plural)'
    const s = run(ev({ type: 'coach', text: fix, clean: false }),
                  ev({ type: 'coach', text: '💡 Feedback: Perfectly natural!', clean: true }),
                  ev({ type: 'coach', text: fix, clean: false }),
                  ev({ type: 'coach', text: '💡 Feedback:\n- ❌ "I go" → ✅ "I went"', clean: false }))
    expect(s.fixes.map((f) => [f.was, f.now])).toEqual([['two bottle', 'two bottles'], ['I go', 'I went']])
  })
})

describe('the drill', () => {
  it('advances on a right answer, stays with a message on a wrong one, closes at zero', () => {
    let s = run(ev({ type: 'drill', target: 'two bottles', remaining: 2 }))
    s = reduce(s, { type: 'drillResult', correct: false, remaining: 2 })
    expect(s.drill).toMatchObject({ target: 'two bottles', msg: '❌ Almost. Type it exactly as shown: "two bottles"' })
    s = reduce(s, { type: 'drillResult', correct: true, remaining: 1, target: 'I went' })
    expect(s.drill).toEqual({ target: 'I went', remaining: 1, msg: '' })
    expect(reduce(s, { type: 'drillResult', correct: true, remaining: 0 }).drill).toBeNull()
  })
})

describe('ending', () => {
  it('a normal end does not tell the learner to reload when the stream drops', () => {
    const s = run(ev({ type: 'finished', tasks_done: 2, tasks_total: 3, tasks_missed: 1 }),
                  { type: 'streamLost', fatal: true })
    expect(s.summary).toMatchObject({ done: 2, outOf: 3, missed: 1 })
    expect(s.banner).toBeNull()
    // nor "reconnecting" — seen on the summary in a playtest
    expect(reduce(s, { type: 'streamLost', fatal: false }).banner).toBeNull()
  })

  it('the closed event from /end marks the end expected, whichever arrives first', () => {
    const s = run(ev({ type: 'closed' }), { type: 'streamLost', fatal: false }, { type: 'streamLost', fatal: true })
    expect(s.banner).toBeNull()
    const other = run({ type: 'streamLost', fatal: false }, ev({ type: 'closed' }))
    expect(other.banner).toBeNull()
  })

  it('a turn that could not be sent reopens the box and takes the line back', () => {
    const s = run(ev({ type: 'state', state: 'awaiting_input' }), { type: 'sent', text: '<system>' },
                  { type: 'turnFailed', text: 'empty message' })
    expect(s.open).toBe(true)
    expect(s.thinking).toBe(false)
    expect(s.log).toHaveLength(0)
    expect(s.banner?.text).toBe('empty message')
  })

  it('reviewing the transcript sets the summary aside, and it can come back', () => {
    let s = run(ev({ type: 'finished', tasks_done: 1, tasks_total: 3, tasks_missed: 0 }), { type: 'reviewing' })
    expect(s.reviewing).toBe(true)
    expect(s.summary).not.toBeNull()
    s = reduce(s, { type: 'backToSummary' })
    expect(s.reviewing).toBe(false)
  })

  it('a session that died on its own does say so', () => {
    const s = run({ type: 'streamLost', fatal: true })
    expect(s.banner).toMatchObject({ fatal: true })
    expect(s.open).toBe(false)
  })

  it('practising again starts clean, so a later drop is reported again', () => {
    const s = run(ev({ type: 'finished', tasks_done: 1, tasks_total: 3, tasks_missed: 2 }),
                  { type: 'started', header: { ...HEADER, session: 'next' } })
    expect(s.endedOnPurpose).toBe(false)
    expect(s.summary).toBeNull()
    expect(s.log).toHaveLength(0)
  })

  it('colours the score by the score, not by having finished', () => {
    expect(scoreClass(0, 10)).toBe('big none')
    expect(scoreClass(3, 10)).toBe('big')
    expect(scoreClass(6, 10)).toBe('big most')
  })

  it('says what is next in the learner\'s language', () => {
    expect(whatsNext('English', { next_rank: 'mastered', plays_needed: 2 }, 1))
      .toBe('Play 2 more times to reach Mastered · 1 word waiting to be practised')
    expect(whatsNext('Japanese', { next_rank: 'experienced', pct_needed: 10 })).toBe('ベストスコアをあと10%上げると「経験者」に')
  })
})

describe('resuming after a reload', () => {
  const snap = (over: Partial<Snapshot>): Snapshot => ({
    ...HEADER, state: 'awaiting_input', tasks: [task('a', { current: true })],
    messages: [{ role: 'assistant', content: 'Hi.' }, { role: 'user', content: 'Hello!' }],
    words: ['latte'], drill: [], tasks_done: 0, tasks_missed: 0, ...over,
  })

  it('rebuilds the transcript, the words and the input state', () => {
    const s = reduce(initialState(), { type: 'resumed', snap: snap({}) })
    expect(s.log.map((l) => l.kind === 'turn' && [l.who, l.text])).toEqual([['Barista', 'Hi.'], ['You', 'Hello!']])
    expect(s.words).toEqual(['latte'])
    expect(s.open).toBe(true)
    expect(s.banner?.text).toBe('Welcome back — your session has been restored.')
  })

  it('puts an open drill back, since there is no other way out of it', () => {
    const s = reduce(initialState(), { type: 'resumed', snap: snap({ state: 'drill', drill: ['two bottles', 'I went'] }) })
    expect(s.drill).toEqual({ target: 'two bottles', remaining: 2, msg: '' })
  })

  it('lands on the summary for a session that already finished', () => {
    const s = reduce(initialState(), { type: 'resumed', snap: snap({ state: 'finished', tasks_done: 3 }) })
    expect(s.summary).toMatchObject({ done: 3, outOf: 3 })
    expect(s.endedOnPurpose).toBe(true)
  })
})
