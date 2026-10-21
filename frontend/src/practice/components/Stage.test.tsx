import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { Stage } from './Stage'
import { initialState, type SessionState } from '../session'

const withArt = (over: Partial<SessionState> = {}, scenario = 'Coffee Shop'): SessionState => ({
  ...initialState(),
  header: { scenario, place: 'A café', speaker: 'Barista', mood: '· chatty and friendly', total: 10 },
  art: { scenario, speaker: 'Barista', mood: 'chatty and friendly, happy to chat' },
  ...over,
})

const stage = (s: SessionState) => render(<Stage state={s} scale={2} />).container

describe('the stage, a postcard (#62)', () => {
  it('draws nothing before a session has its art', () => {
    expect(stage(initialState()).innerHTML).toBe('')
  })

  it('draws the café in pixels, at a whole-number scale, with the NOW AT tag', () => {
    const c = stage(withArt())
    const el = c.querySelector('#stage') as HTMLElement
    expect(el.getAttribute('aria-hidden')).toBe('true')
    expect(el.dataset.scene).toBe('cafe')
    expect(el.style.width).toBe('416px')
    expect(c.querySelector('canvas')?.width).toBe(208)
    expect(c.textContent).toContain('NOW AT')
    expect(c.textContent).toContain('Barista')
    expect(c.textContent).toContain('chatty and friendly')
  })

  it('keeps the older drawing, with its sign, for a scenario not yet redrawn', () => {
    const c = stage(withArt({}, 'Pharmacy'))
    expect((c.querySelector('#stage') as HTMLElement).dataset.scene).toBe('counter')
    expect(c.textContent).toContain('PHARMACY')
    expect(c.querySelector('.stage-speaker canvas')).not.toBeNull()
  })

  it('starts on the mood face and changes it with the reaction', () => {
    const face = (s: SessionState) => (stage(s).querySelector('#stage') as HTMLElement).dataset.expression
    expect(face(withArt())).toBe('smile')
    expect(face(withArt({ reaction: 'mistake' }))).toBe('concern')
    expect(face(withArt({ reaction: 'fixed' }))).toBe('grin')
  })

  it('speaks the learner language: the sign and the tag', () => {
    const c = stage(withArt({ lang: 'Japanese' }, 'Pharmacy'))
    expect(c.textContent).toContain('薬局')
    expect(c.textContent).toContain('いまここ')
  })
})
