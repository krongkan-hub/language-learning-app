import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { Character } from './Character'
import { expressionForMood, lookFor, outfitFor, type Outfit } from './characters'

// Every speaker in app/scenarios/data, with the outfit its scenarios call for.
// A new speaker in the catalogue fails test_every_catalogue_speaker_is_dressed
// (dev/tests) until it is added here.
const DRESSED: Record<string, Outfit> = {
  'Receptionist': 'blazer', 'Clerk': 'blazer', 'Agent': 'blazer', 'Consultant': 'suit',
  'Technician': 'overalls', 'Interviewer': 'suit', 'Guide': 'blazer', 'Staff': 'blazer',
  'Cashier': 'apron', 'Advisor': 'suit', 'Vendor': 'apron', 'Waiter': 'vest', 'Barista': 'apron',
  'Pharmacist': 'whitecoat', 'Officer': 'uniform', 'Sales Assistant': 'blazer',
  'Ticket Officer': 'blazer', 'Banker': 'suit', 'Property Manager': 'suit', 'Bookseller': 'cardigan',
  'Stylist': 'smock', 'Driver': 'tee', 'Farmer': 'overalls', 'Veterinarian': 'whitecoat',
  'Baker': 'apron', 'Postal Clerk': 'blazer', 'Duty Officer': 'uniform', 'Shopkeeper': 'apron',
  'Specialist': 'blazer', 'Admissions Officer': 'blazer', 'Librarian': 'cardigan', 'Florist': 'apron',
  'Scoop Staff': 'apron', 'Sommelier': 'vest', 'Ranger': 'ranger', 'Curator': 'cardigan',
  'Tailor': 'tailor', 'Real Estate Agent': 'suit', 'Mechanic': 'overalls', 'Assistant': 'blazer',
  'Transit Officer': 'uniform', 'Game Master': 'hoodie', 'Host': 'blazer', 'Artist': 'smock',
  'Chef Instructor': 'chef', 'Cobbler': 'apron', 'Community Manager': 'tee', 'Neighbor': 'tee',
  'Nurse Morgan': 'whitecoat', 'Supervisor Karen': 'blazer', 'Adjuster Miller': 'suit',
  'Founder Sam': 'hoodie', 'Officer Vance': 'uniform', 'Landlord Mr. Sterling': 'suit',
  'Inspector Zhao': 'uniform', 'Director Henderson': 'suit', 'Loan Officer Arthur': 'suit',
  'Planner Celeste': 'blazer',
}

describe('character kit', () => {
  it('dresses every catalogue speaker for the job its scenarios show', () => {
    expect(Object.keys(DRESSED)).toHaveLength(58)
    for (const [speaker, outfit] of Object.entries(DRESSED)) {
      expect([speaker, outfitFor(speaker)]).toEqual([speaker, outfit])
    }
    expect(outfitFor('Somebody new')).toBe('blazer')            // a safe default
  })

  it('keeps a speaker looking the same across releases', () => {
    // Pinned: changing the hash, a palette or the hair list re-draws every
    // face the learner already knows. Update deliberately, or not at all.
    expect(lookFor('Barista')).toEqual({
      outfit: 'apron', hair: 'bun', hairColor: '#A7703F', skin: '#EBC3A0',
      glasses: false, beard: false, accent: '#2F4858',
    })
    expect(lookFor('Receptionist')).toMatchObject({ outfit: 'blazer', hair: 'bald', glasses: true })
  })

  it('never draws a bun through a hat', () => {
    for (const speaker of Object.keys(DRESSED)) {
      const look = lookFor(speaker)
      if (['uniform', 'ranger', 'chef'].includes(look.outfit)) expect(look.hair).not.toBe('bun')
    }
  })

  it('starts each of the six NPC moods on its own face', () => {
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
