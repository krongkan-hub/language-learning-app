import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { Scene } from './Scene'
import { SCENES, sceneFor } from './scenes'

describe('scene kit', () => {
  it('has a backdrop for each of the 80 scenarios', () => {
    // dev/tests/test_scene_kit.py checks these names against app/scenarios/data.
    expect(Object.keys(SCENES)).toHaveLength(80)
  })

  it('draws every backdrop, in both languages, with its sign', () => {
    for (const [name, spec] of Object.entries(SCENES)) {
      for (const [language, sign] of [['English', spec.sign[0]], ['Japanese', spec.sign[1]]]) {
        const { container, unmount } = render(<Scene spec={spec} language={language} />)
        expect(container.querySelector('svg'), name).not.toBeNull()
        expect(container.textContent, `${name} (${language})`).toContain(sign)
        unmount()
      }
    }
  })

  it('keeps every sign readable: no text drawn below 14 units (about 8px at thumbnail size)', () => {
    // Review #52: "PRIVATE BANKING" came out at 9 units in a 130-wide box.
    for (const [name, spec] of Object.entries(SCENES)) {
      for (const language of ['English', 'Japanese']) {
        const { container, unmount } = render(<Scene spec={spec} language={language} />)
        for (const t of container.querySelectorAll('text')) {
          expect(Number(t.getAttribute('font-size')), `${name} (${language}): ${t.textContent}`).toBeGreaterThanOrEqual(14)
        }
        unmount()
      }
    }
  })

  it('gives a scenario the catalogue does not know a plain desk, not a crash', () => {
    expect(sceneFor('A scenario added tomorrow').template).toBe('desk')
  })

  it('gives the review chat a café and an explain session a plain room, not a front desk', () => {
    expect(sceneFor('Practice Your Mistakes')).toMatchObject({ template: 'counter', goods: 'cups' })
    expect(sceneFor('').template).toBe('home')
  })

  it('is decoration: hidden from screen readers', () => {
    const { container } = render(<Scene spec={SCENES['Coffee Shop']} />)
    expect(container.firstElementChild?.getAttribute('aria-hidden')).toBe('true')
  })
})
