// The accessibility pass, checked on the rendered page: every control has a
// name, NPC turns reach a screen reader exactly once, the drill is a real
// modal, and the scenario cards work from a keyboard.
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { Practice } from './Practice'
import { emit, installServer } from './fakeServer'

beforeEach(() => { installServer({
  'GET /api/scenarios': { scenarios: [
    { name: 'coffee', display_name: 'Coffee Shop', place: 'A café', mastery_label: 'Newbie', plays: 2 }] },
}) })
afterEach(() => vi.unstubAllGlobals())

async function startSession() {
  render(<Practice />)
  await userEvent.click(await screen.findByRole('button', { name: /^Conversation/ }))
  await waitFor(() => expect(screen.queryByText('Coffee Shop', { selector: '#hScenario' })).toBeInTheDocument())
}

describe('names', () => {
  const allNamed = (min: number) => {
    const controls = [...screen.getAllByRole('button', { hidden: true }), ...screen.getAllByRole('textbox', { hidden: true })]
    expect(controls.length).toBeGreaterThanOrEqual(min)
    for (const c of controls) expect(c).toHaveAccessibleName()
  }

  it('every button and text box has an accessible name, on the landing page and in a session', async () => {
    render(<Practice />)
    await userEvent.click(screen.getByRole('button', { name: /Browse/ }))
    await screen.findByRole('button', { name: /Coffee Shop/ })
    allNamed(8)           // the cover's nav and language switch, search + close, a scenario
    await userEvent.click(screen.getByRole('button', { name: /Coffee Shop/ }))
    await waitFor(() => expect(document.getElementById('setup')).toBeNull())
    emit({ type: 'drill', target: 'two bottles', remaining: 1 })
    allNamed(6)           // skip, end, send, the message box, the drill's box and OK
  })
})

describe('the live region', () => {
  it('announces a finished NPC turn once, and the visible log is not itself live', async () => {
    await startSession()
    expect(screen.getByRole('log')).not.toHaveAttribute('aria-live')
    emit({ type: 'sentence', text: 'Hello.' }, { type: 'sentence', text: 'What can I get you?' })
    const live = document.getElementById('srAnnounce')!
    expect(live).toHaveAttribute('aria-live', 'polite')
    expect(live).toHaveClass('sr-only')
    expect(live).toHaveTextContent('')                     // not while it streams
    emit({ type: 'npc', text: 'Hello. What can I get you?' })
    expect(live).toHaveTextContent('Barista: Hello. What can I get you?')
  })
})

describe('the drill', () => {
  it('is a labelled modal dialog that holds Tab and sends Escape to End', async () => {
    await startSession()
    emit({ type: 'drill', target: 'two bottles', remaining: 2 })
    const dialog = screen.getByRole('dialog', { name: 'Write it again, right:' })
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    const input = screen.getByLabelText('Retype the correction shown above')
    const ok = screen.getByRole('button', { name: 'OK' })
    expect(input).toHaveFocus()

    ok.focus()
    fireEvent.keyDown(ok, { key: 'Tab' })
    expect(input).toHaveFocus()                            // wraps forward
    fireEvent.keyDown(input, { key: 'Tab', shiftKey: true })
    expect(ok).toHaveFocus()                               // and backward

    fireEvent.keyDown(ok, { key: 'Escape' })
    expect(screen.getByRole('button', { name: 'End' })).toHaveFocus()
    expect(dialog).toBeInTheDocument()                     // Escape is not a way to skip it
  })
})

describe('the scenario browser', () => {
  it('cards are buttons with a readable name, and Enter picks one', async () => {
    const calls = installServer({
      'GET /api/scenarios': { scenarios: [
        { name: 'coffee', display_name: 'Coffee Shop', place: 'A café', mastery_label: 'Newbie', plays: 2 }] },
    })
    render(<Practice />)
    await userEvent.click(screen.getByRole('button', { name: /Browse/ }))
    const card = await screen.findByRole('button', { name: 'Coffee Shop, A café, Newbie, 2×' })
    expect(card).toHaveAttribute('tabindex', '0')
    card.focus()
    await act(async () => { fireEvent.keyDown(card, { key: 'Enter' }) })
    await waitFor(() => expect(calls.find((c) => c.method === 'POST')?.body)
      .toEqual({ language: 'English', scenario: 'coffee', tasks: 10 }))
  })
})
