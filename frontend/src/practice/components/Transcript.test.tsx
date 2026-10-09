import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { Transcript, circled } from './Transcript'
import type { LogItem } from '../session'

const ART = { scenario: 'Coffee Shop', speaker: 'Barista', mood: 'calm and unhurried' }
const LOG: LogItem[] = [
  { id: 1, kind: 'turn', who: 'Barista', text: 'What can I get you?', cls: 'npc' },
  { id: 2, kind: 'turn', who: 'You', text: 'How much it cost? I have two dollar.', cls: 'you' },
]

describe('the notebook page (#50b)', () => {
  it('circles each corrected span where the learner wrote it, without its full stop', () => {
    const { container } = render(<>{circled('How much it cost? I have two dollar.', ['How much it cost?', 'I have two dollar.'])}</>)
    const marks = [...container.querySelectorAll('.redmark')].map((m) => m.textContent)
    expect(marks).toEqual(['How much it cost', 'I have two dollar'])
    expect(container.textContent).toBe('How much it cost? I have two dollar.')   // the words stay intact
  })

  it('leaves a line alone when nothing in it was corrected, and survives regex characters', () => {
    expect(circled('All good here.', ['two dollar'])).toEqual(['All good here.'])
    const { container } = render(<>{circled('Is it (really) $5?', ['(really) $5'])}</>)
    expect(container.querySelector('.redmark')?.textContent).toBe('(really) $5')
  })

  it("circles only the learner's lines and gives the speaker's lines a face", () => {
    const { container } = render(
      <Transcript log={LOG} drillOpen={false} fixes={[{ was: 'it cost', now: 'does it cost', why: '' }]} art={ART} />)
    expect(container.querySelectorAll('.redmark')).toHaveLength(1)
    expect(container.querySelectorAll('.turn.npc .face svg')).toHaveLength(1)
    expect(container.querySelector('#log')?.className).toContain('paper')
  })
})
