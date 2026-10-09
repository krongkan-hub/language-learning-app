import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { Stage } from './Stage'
import { initialState, type SessionState } from '../session'

const withArt = (over: Partial<SessionState> = {}): SessionState => ({
  ...initialState(),
  header: { scenario: 'Coffee Shop', place: 'A café', speaker: 'Barista', mood: '· chatty and friendly', total: 10 },
  art: { scenario: 'Coffee Shop', speaker: 'Barista', mood: 'chatty and friendly, happy to chat' },
  ...over,
})

describe('the stage', () => {
  it('draws nothing before a session has its art', () => {
    const { container } = render(<Stage state={initialState()} />)
    expect(container.innerHTML).toBe('')
  })

  it('draws the scene with its sign, the speaker and the name plate', () => {
    const { container } = render(<Stage state={withArt()} />)
    expect(container.textContent).toContain('COFFEE')
    expect(container.textContent).toContain('Barista')
    expect(container.textContent).toContain('chatty and friendly')
    expect(container.querySelector('#stage')?.getAttribute('aria-hidden')).toBe('true')
  })

  it('starts on the mood face and changes it with the reaction', () => {
    const face = (s: SessionState) => render(<Stage state={s} />).container
      .querySelector('.stage-speaker')?.getAttribute('data-expression')
    expect(face(withArt())).toBe('smile')
    expect(face(withArt({ reaction: 'mistake' }))).toBe('concern')
    expect(face(withArt({ reaction: 'fixed' }))).toBe('grin')
  })

  it('puts the sign in the learner language', () => {
    const { container } = render(<Stage state={withArt({ lang: 'Japanese' })} />)
    expect(container.textContent).toContain('カフェ')
  })
})
