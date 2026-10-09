import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { Scene } from './Scene'
import { SCENES, sceneFor } from './scenes'

describe('scene kit', () => {
  it('has a backdrop for each of the 80 scenarios', () => {
    // dev/tests/test_art_kit.py checks these names against app/scenarios/data.
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

  it('gives a scenario the catalogue does not know a plain desk, not a crash', () => {
    expect(sceneFor('A scenario added tomorrow').template).toBe('desk')
  })

  it('is decoration: hidden from screen readers', () => {
    const { container } = render(<Scene spec={SCENES['Coffee Shop']} />)
    expect(container.firstElementChild?.getAttribute('aria-hidden')).toBe('true')
  })
})
