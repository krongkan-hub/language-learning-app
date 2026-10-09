// Whole-page behaviour: sending a turn, resuming after a reload, ending, and
// the details that were each a bug once.
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Practice } from './Practice'
import { Transcript } from './components/Transcript'
import { emit, FakeEventSource, HEADER, installServer } from './fakeServer'
import type { ReactElement } from 'react'
import type { LogItem } from './session'

afterEach(() => vi.unstubAllGlobals())

// Today's page (#50c): pick the language on the cover, then a card.
async function startSession(card: RegExp = /^Conversation/, language?: '日本語') {
  render(<Practice />)
  if (language) await userEvent.click(screen.getByRole('button', { name: language }))
  await userEvent.click(await screen.findByRole('button', { name: card }))
  await waitFor(() => expect(document.getElementById('setup')).toBeNull())
}

describe('a turn', () => {
  it('posts what the learner typed and shows it at once', async () => {
    const calls = installServer()
    await startSession()
    emit({ type: 'state', state: 'awaiting_input' })
    const box = screen.getByRole('textbox', { name: 'Type your reply…' })
    expect(box).toHaveFocus()
    await userEvent.type(box, 'A latte, please{Enter}')
    expect(screen.getByRole('log')).toHaveTextContent('A latte, please')
    expect(calls.at(-1)).toEqual({ method: 'POST', url: '/api/turn/s1', body: { text: 'A latte, please' } })

    // while the turn finishes the next message can be drafted, not sent
    expect(box).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    const before = calls.length
    await userEvent.type(box, 'And a croissant{Enter}')
    expect(calls.length).toBe(before)
    expect(box).toHaveValue('And a croissant')
  })
})

describe('keys and double clicks', () => {
  it('Enter that confirms a Japanese IME conversion does not send', async () => {
    const calls = installServer()
    await startSession()
    emit({ type: 'state', state: 'awaiting_input' })
    const box = screen.getByRole('textbox', { name: 'Type your reply…' })
    await userEvent.type(box, 'こーひー')
    fireEvent.keyDown(box, { key: 'Enter', isComposing: true })
    fireEvent.keyDown(box, { key: 'Enter', keyCode: 229 })
    expect(calls.filter((c) => c.url.startsWith('/api/turn'))).toHaveLength(0)
    fireEvent.keyDown(box, { key: 'Enter' })
    await waitFor(() => expect(calls.filter((c) => c.url.startsWith('/api/turn'))).toHaveLength(1))
  })

  it('a double-clicked Skip skips one task', async () => {
    let release: () => void = () => {}
    const calls = installServer({ 'POST /api/skip/s1': () => new Promise<object>((r) => { release = () => r({}) }) })
    await startSession()
    emit({ type: 'state', state: 'awaiting_input' })
    const skip = screen.getByRole('button', { name: 'Skip task' })
    fireEvent.click(skip)
    fireEvent.click(skip)
    await act(async () => { release() })
    expect(calls.filter((c) => c.url === '/api/skip/s1')).toHaveLength(1)
  })

  it('a failed send gives the text back', async () => {
    const calls = installServer({ 'POST /api/turn/s1': 400 })
    await startSession()
    emit({ type: 'state', state: 'awaiting_input' })
    const box = screen.getByRole('textbox', { name: 'Type your reply…' })
    await userEvent.type(box, '<system>{Enter}')
    await waitFor(() => expect(document.getElementById('banner')).not.toBeNull())
    expect(calls.some((c) => c.url === '/api/turn/s1')).toBe(true)      // it was sent, and refused
    expect(box).toHaveValue('<system>')
    expect(screen.getByRole('log')).not.toHaveTextContent('<system>')
    expect(screen.getByRole('button', { name: 'Send' })).toBeEnabled()
  })

  it('follows the session language for screen readers', async () => {
    installServer({ 'POST /api/session': { ...HEADER, language: 'Japanese' } })
    await startSession(/^会話/, '日本語')
    await waitFor(() => expect(document.documentElement.lang).toBe('ja'))
  })
})

describe('practice your mistakes', () => {
  it('is up next once the coach has corrected something, and starts a review session', async () => {
    const calls = installServer({
      'GET /api/today': { review: [{ was: 'two bottle', fix: 'two bottles', occurrences: 2 }], recent: [],
                          done_today: 0, streak: 0 },
      'POST /api/session': { ...HEADER, mode: 'review', scenario: 'Practice Your Mistakes' } })
    render(<Practice />)
    expect(await screen.findByText('two bottles')).toBeInTheDocument()     // the red mark it will redo
    await userEvent.click(screen.getByRole('button', { name: 'Start the redo' }))
    await waitFor(() => expect(calls.find((c) => c.method === 'POST')?.body)
      .toEqual({ language: 'English', mode: 'review' }))
  })

  it('is not offered before the coach has corrected anything', async () => {
    installServer()                         // no review items
    render(<Practice />)
    await screen.findByRole('button', { name: 'Start' })                   // a conversation is up next
    expect(screen.queryByRole('button', { name: 'Start the redo' })).toBeNull()
  })
})

describe('the transcript', () => {
  it('pins to the bottom on every append and on both drill transitions', () => {
    const item = (id: number): LogItem => ({ id, kind: 'turn', who: 'You', text: `line ${id}`, cls: 'you' })
    const { rerender } = render(<Transcript log={[item(1)]} drillOpen={false} />)
    const log = screen.getByRole('log')
    let height = 500
    Object.defineProperty(log, 'scrollHeight', { get: () => height })
    const check = (ui: ReactElement) => { log.scrollTop = 0; height += 50; rerender(ui); expect(log.scrollTop).toBe(height) }
    const two = [item(1), item(2)]                  // one array: only drillOpen changes below
    check(<Transcript log={two} drillOpen={false} />)   // an append
    check(<Transcript log={two} drillOpen={true} />)    // the drill opens and shrinks the log
    check(<Transcript log={two} drillOpen={false} />)   // and closes
  })
})

describe('resuming after a reload', () => {
  const snapshot = {
    ...HEADER, state: 'awaiting_input', tasks: [], words: ['latte'], drill: [],
    messages: [{ role: 'assistant', content: 'Welcome back.' }], tasks_done: 0, tasks_missed: 0,
  }

  it('stores the session id, and a reload picks the session back up', async () => {
    installServer({ 'GET /api/session/s1': snapshot })
    await startSession()
    expect(sessionStorage.getItem('coach.sid')).toBe('s1')

    cleanup()                                      // the reload
    FakeEventSource.last = null                    // so the stream below is the resumed one
    render(<Practice />)
    expect(await screen.findByText('Welcome back.')).toBeInTheDocument()
    expect((FakeEventSource.last as FakeEventSource | null)?.url).toBe('/api/stream/s1')
  })

  it('forgets a session the server no longer has', async () => {
    installServer()                                // GET /api/session/gone -> 404
    sessionStorage.setItem('coach.sid', 'gone')
    render(<Practice />)
    await waitFor(() => expect(sessionStorage.getItem('coach.sid')).toBeNull())
    expect(document.getElementById('setup')).not.toBeNull()
  })
})

describe('explain mode', () => {
  it('hides the vocabulary panel, which nothing would fill', async () => {
    installServer({ 'POST /api/session': { ...HEADER, mode: 'explain' } })
    await startSession(/^Explain/)
    expect(document.getElementById('vocabBox')).not.toBeVisible()
  })
})

describe('ending', () => {
  it('End shows the summary, forgets the session, and a dropped stream says nothing', async () => {
    installServer({ 'POST /api/session/s1/end': { tasks_done: 0, tasks_skipped: 1, words_due: 2 } })
    await startSession()
    await userEvent.click(screen.getByRole('button', { name: 'End' }))
    expect(await screen.findByText('0/3')).toHaveClass('big', 'none')
    // nothing done: the page is closed, not scolded, and earns no 花丸
    expect(screen.getByRole('dialog', { name: 'Page closed' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Practice again' })).toHaveFocus()
    expect(screen.getByText('2 words waiting to be practiced')).toBeInTheDocument()
    expect(sessionStorage.getItem('coach.sid')).toBeNull()
    act(() => { FakeEventSource.last!.readyState = FakeEventSource.CLOSED; FakeEventSource.last!.onerror!() })
    expect(document.getElementById('banner')).toBeNull()
  })

  it('a stream that dies on its own is reported, after a few quiet retries', async () => {
    installServer()
    await startSession()
    const es = FakeEventSource.last!
    es.readyState = FakeEventSource.CONNECTING
    act(() => { es.onerror!(); es.onerror!(); es.onerror!() })
    expect(document.getElementById('banner')).toHaveTextContent('reconnecting')
    act(() => { es.onerror!() })
    expect(es.closed).toBe(true)
    expect(document.getElementById('banner')).toHaveTextContent('Reload the page to start a new one')
  })
})

describe("today's page (#50c)", () => {
  it('shows the 花丸 earned and the streak once a page is done today', async () => {
    installServer({ 'GET /api/today': { review: [], recent: [], done_today: 1, streak: 4 } })
    render(<Practice />)
    expect(await screen.findByText("Today's page is done — 花丸")).toBeInTheDocument()
    expect(screen.getByText('4-day streak')).toBeInTheDocument()
  })

  it('lists the latest red marks, and switches the whole page to the language picked', async () => {
    const calls = installServer({ 'GET /api/today': { review: [], recent: [{ was: 'I go yesterday', fix: 'I went yesterday' }],
                                                      done_today: 0, streak: 0 } })
    render(<Practice />)
    expect(await screen.findByText('I went yesterday')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '日本語' }))
    expect(await screen.findByText('会話をはじめる')).toBeInTheDocument()
    expect(calls.some((c) => c.url === '/api/today?language=Japanese')).toBe(true)
  })
})


describe('page complete (#50d)', () => {
  it('earns the 花丸 with a task done, ends on the best clean line, and goes back to Today', async () => {
    installServer({ 'POST /api/session/s1/end': { tasks_done: 2, tasks_skipped: 0, words_due: 0 } })
    await startSession()
    emit({ type: 'state', state: 'awaiting_input' })
    await userEvent.type(screen.getByRole('textbox', { name: 'Type your reply…' }),
                         'Could I get a large latte with oat milk?{Enter}')
    await userEvent.click(screen.getByRole('button', { name: 'End' }))
    const page = await screen.findByRole('dialog', { name: 'Page complete' })
    expect(within(page).getByText('Could I get a large latte with oat milk?')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: "Today's page" }))
    expect(document.getElementById('setup')).not.toBeNull()
  })
})
