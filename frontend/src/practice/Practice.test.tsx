// Whole-page behaviour: sending a turn, resuming after a reload, ending, and
// the details that were each a bug once.
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Practice } from './Practice'
import { Transcript } from './components/Transcript'
import { emit, FakeEventSource, HEADER, installServer } from './fakeServer'
import type { ReactElement } from 'react'
import type { LogItem } from './session'

afterEach(() => vi.unstubAllGlobals())

async function startSession(label: RegExp = /^English/) {
  render(<Practice />)
  await userEvent.click(screen.getByRole('button', { name: label }))
  await waitFor(() => expect(document.getElementById('setup')).toBeNull())
}

describe('a turn', () => {
  it('posts what the learner typed and shows it at once', async () => {
    const calls = installServer()
    await startSession()
    emit({ type: 'state', state: 'awaiting_input' })
    const box = screen.getByRole('textbox', { name: 'Type your message' })
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
    const box = screen.getByRole('textbox', { name: 'Type your message' })
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
    installServer({ 'POST /api/turn/s1': 400 })
    await startSession()
    emit({ type: 'state', state: 'awaiting_input' })
    const box = screen.getByRole('textbox', { name: 'Type your message' })
    await userEvent.type(box, '<system>{Enter}')
    await waitFor(() => expect(box).toHaveValue('<system>'))
    expect(screen.getByRole('button', { name: 'Send' })).toBeEnabled()
  })

  it('follows the session language for screen readers', async () => {
    installServer({ 'POST /api/session': { ...HEADER, language: 'Japanese' } })
    await startSession(/^日本語/)
    await waitFor(() => expect(document.documentElement.lang).toBe('ja'))
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
    check(<Transcript log={[item(1), item(2)]} drillOpen={false} />)   // an append
    check(<Transcript log={[item(1), item(2)]} drillOpen={true} />)    // the drill opens and shrinks the log
    check(<Transcript log={[item(1), item(2)]} drillOpen={false} />)   // and closes
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
    render(<Practice />)
    expect(await screen.findByText('Welcome back.')).toBeInTheDocument()
    expect(FakeEventSource.last?.url).toBe('/api/stream/s1')
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
    await startSession(/Explain · English/)
    expect(document.getElementById('vocabBox')).not.toBeVisible()
  })
})

describe('ending', () => {
  it('End shows the summary, forgets the session, and a dropped stream says nothing', async () => {
    installServer({ 'POST /api/session/s1/end': { tasks_done: 0, tasks_skipped: 1, words_due: 2 } })
    await startSession()
    await userEvent.click(screen.getByRole('button', { name: 'End' }))
    expect(await screen.findByText('0/3')).toHaveClass('big', 'none')
    expect(screen.getByRole('dialog', { name: '0/3' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Practise again' })).toHaveFocus()
    expect(screen.getByText('2 words waiting to be practised')).toBeInTheDocument()
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
    expect(document.getElementById('banner')).toHaveTextContent('Reload to start a new one')
  })
})
