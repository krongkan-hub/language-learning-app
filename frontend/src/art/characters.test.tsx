import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { Bust } from './pixel/Bust'
import { HAIRS, OUTFITS } from './pixel/parts'
import { MOODS } from './pixel/faces'
import { BY_SCENARIO, expressionForMood, FACE, lookFor, outfitFor, SPEAKERS } from './characters'
import { SCENES } from './scenes'

// Every speaker in app/scenarios/data, with the outfit its job calls for
// (docs/design/pixel/speakers.md). A new speaker in the catalogue fails
// test_every_catalogue_speaker_is_dressed (dev/tests) until it is added here.
const DRESSED: Record<string, string> = {
  'Receptionist': 'blazer', 'Clerk': 'polo', 'Agent': 'blazer', 'Consultant': 'polo',
  'Technician': 'polo', 'Interviewer': 'blazer', 'Guide': 'blazer', 'Staff': 'tee',
  'Cashier': 'polo', 'Advisor': 'polo', 'Vendor': 'apron', 'Waiter': 'barvest', 'Barista': 'apron',
  'Pharmacist': 'coat', 'Officer': 'uniform', 'Sales Assistant': 'blazer',
  'Ticket Officer': 'uniform', 'Banker': 'blazer', 'Property Manager': 'blazer', 'Bookseller': 'cardigan',
  'Stylist': 'apron', 'Driver': 'polo', 'Farmer': 'flannel', 'Veterinarian': 'coat',
  'Baker': 'apron', 'Postal Clerk': 'polo', 'Duty Officer': 'uniform', 'Shopkeeper': 'apron',
  'Specialist': 'polo', 'Admissions Officer': 'cardigan', 'Librarian': 'cardigan', 'Florist': 'apron',
  'Scoop Staff': 'apron', 'Sommelier': 'barvest', 'Ranger': 'uniform', 'Curator': 'blazer',
  'Tailor': 'barvest', 'Real Estate Agent': 'blazer', 'Mechanic': 'overalls', 'Assistant': 'coat',
  'Transit Officer': 'uniform', 'Game Master': 'hoodie', 'Host': 'blazer', 'Artist': 'tank',
  'Chef Instructor': 'chef', 'Cobbler': 'apron', 'Community Manager': 'tee', 'Neighbor': 'tee',
  'Nurse Morgan': 'scrubs', 'Supervisor Karen': 'blazer', 'Adjuster Miller': 'blazer',
  'Founder Sam': 'hoodie', 'Officer Vance': 'uniform', 'Landlord Mr. Sterling': 'blazer',
  'Inspector Zhao': 'uniform', 'Director Henderson': 'blazer', 'Loan Officer Arthur': 'blazer',
  'Planner Celeste': 'blazer',
}

describe('the speakers, drawn with the pixel kit (#62)', () => {
  it('dresses every catalogue speaker for the job, and only them', () => {
    expect(Object.keys(DRESSED)).toHaveLength(58)
    expect(Object.keys(SPEAKERS).sort()).toEqual(Object.keys(DRESSED).sort())
    for (const [speaker, outfit] of Object.entries(DRESSED)) expect([speaker, outfitFor(speaker)]).toEqual([speaker, outfit])
    expect(outfitFor('Friend')).toBe('hoodie')                  // the review chat
    expect(outfitFor('Listener')).toBe('cardigan')              // explain mode
    expect(outfitFor('Somebody new')).toBe('blazer')            // a safe default
  })

  it('re-dresses a speaker whose name works another job in a scenario', () => {
    expect(outfitFor('Receptionist', 'Hotel Check-in')).toBe('blazer')
    expect(outfitFor('Receptionist', 'Dental Clinic Checkup')).toBe('scrubs')
    expect(lookFor('Technician', 'Ski Resort Pass & Gear')).toMatchObject({ outfit: 'hoodie', hair: 'beanie' })
    // only catalogue scenarios, and only a catalogue speaker is re-dressed
    for (const scenario of Object.keys(BY_SCENARIO)) expect(SCENES).toHaveProperty([scenario])
    expect(outfitFor('Friend', 'Dental Clinic Checkup')).toBe('hoodie')
  })

  it('uses only parts the kit has', () => {
    for (const look of [...Object.values(SPEAKERS), ...Object.values(BY_SCENARIO)]) {
      if (look.outfit) expect(OUTFITS).toContain(look.outfit)
      if (look.hair) expect(Object.keys(HAIRS)).toContain(look.hair)
    }
  })

  it('starts each of the six NPC moods on its own expression, each drawn with a hand-drawn face', () => {
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
    // every one of the kit's six faces is in use
    expect(new Set(Object.values(FACE))).toEqual(new Set(MOODS))
  })

  it('names the drawing for screen readers only when given a title', () => {
    const { container, rerender } = render(<Bust spec={lookFor('Baker')} title="The Baker" />)
    expect(container.querySelector('canvas')?.getAttribute('aria-label')).toBe('The Baker')
    rerender(<Bust spec={lookFor('Baker')} />)
    expect(container.querySelector('canvas')?.getAttribute('aria-hidden')).toBe('true')
  })
})
