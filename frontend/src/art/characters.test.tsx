import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { Character } from './Character'
import { expressionForMood, lookFor, outfitFor } from './characters'

describe('character kit', () => {
  it('draws the same speaker the same way every time', () => {
    expect(lookFor('Barista')).toEqual(lookFor('Barista'))
  })

  it('dresses roles by what they do, longest role first', () => {
    expect(outfitFor('Loan Officer Arthur')).toBe('suit')       // not the police "officer"
    expect(outfitFor('Officer Vance')).toBe('uniform')
    expect(outfitFor('Nurse Morgan')).toBe('whitecoat')
    expect(outfitFor('Chef Instructor')).toBe('chef')
    expect(outfitFor('Somebody new')).toBe('blazer')            // a safe default
  })

  it('starts each of the six NPC moods (app/llm/prompts.py) on its own face', () => {
    const moods = [
      'harried and rushing, keen to keep things moving',
      'chatty and friendly, happy to chat while you work',
      'curt and impatient, giving clipped answers',
      'skeptical and questioning, wanting things spelled out',
      'cheerful but scatterbrained, easily sidetracked',
      'calm and unhurried, taking your time with the customer',
    ]
    const faces = moods.map(expressionForMood)
    expect(new Set(faces).size).toBe(6)
    expect(faces).not.toContain('neutral')
  })

  it('names the drawing for screen readers only when given a title', () => {
    const { container, rerender } = render(<Character look={lookFor('Baker')} title="The Baker" />)
    expect(container.querySelector('svg')?.getAttribute('aria-label')).toBe('The Baker')
    rerender(<Character look={lookFor('Baker')} />)
    expect(container.querySelector('svg')?.getAttribute('aria-hidden')).toBe('true')
  })
})
