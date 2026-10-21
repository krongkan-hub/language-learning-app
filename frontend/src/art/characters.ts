// Who each catalogue speaker looks like, as a pixel-kit spec (#62). The
// catalogue has 58 speakers across 80 scenarios. Each is drawn on purpose,
// dressed for the job, not hashed from the name, so the list can be reviewed:
// docs/design/pixel/speakers.md is this table in prose. Some names work more
// than one job (the Receptionist is at a hotel, a clinic, a spa...), so a
// scenario can re-dress its speaker (BY_SCENARIO).
import type { Mood } from './pixel/faces'
import type { KitSpec } from './pixel/render'

export type Expression =
  | 'neutral' | 'smile' | 'grin' | 'calm' | 'curt' | 'skeptical' | 'harried' | 'concern' | 'surprised'

type Look = Omit<KitSpec, 'mood'>

const L = (outfit: string, cloth: string, hair: string, hairColor: Look['hairColor'], skin: Look['skin'],
  more: Partial<Look> = {}): Look => ({ head: 'oval', outfit, cloth, hair, hairColor, skin, ...more })

// Colours: a muted set that sits on the ticket paper and the café plaster.
const NAVY = '#2f3f6b', CHARCOAL = '#33384a', BLACK = '#2b2a33', WHITE = '#efece4', COAT = '#eef0f2'
const SHIRT = '#efece4', GOLD = '#e2b64a', RED = '#b23a48'

export const SPEAKERS: Record<string, Look> = {
  // the approved kit's own examples (docs/design/pixel/pixel-kit.html)
  'Barista': L('apron', '#5a8f6a', 'ponytail', 'auburn', 'a', { accent: '#3d5f47' }),
  'Pharmacist': L('coat', COAT, 'bob', 'black', 'b', { glasses: true }),
  'Officer': L('uniform', NAVY, 'cap', 'black', 'd', { head: 'square', mustache: true }),
  'Farmer': L('flannel', '#a23f3f', 'strawhat', 'gray', 'c', { head: 'square', hatColor: '#d9b56a', beard: true, old: true }),
  'Vendor': L('apron', '#e07a3f', 'bun', 'black', 'c', { head: 'round', accent: '#3a5ea8' }),
  'Receptionist': L('blazer', '#6e3b5a', 'bob', 'black', 'e', { tie: SHIRT }),
  // food and drink
  'Waiter': L('barvest', '#26272f', 'sidepart', 'black', 'b', { tie: '#2a2a33' }),
  'Sommelier': L('barvest', '#5a2a34', 'sidepart', 'gray', 'a', { tie: BLACK, mustache: true }),
  'Baker': L('apron', SHIRT, 'toque', 'black', 'b', { head: 'round', accent: '#c9a06b', hatColor: '#f4f2ec', mustache: true }),
  'Chef Instructor': L('chef', '#f4f2ec', 'toque', 'black', 'c', { head: 'square', hatColor: '#f4f2ec', badge: '#55505a', stubble: true }),
  'Scoop Staff': L('apron', '#e8a0b0', 'cap', 'brown', 'c', { accent: WHITE, hatColor: '#e8a0b0', badge: WHITE }),
  'Cashier': L('polo', '#8f2a36', 'ponytail', 'black', 'b', { badge: GOLD }),
  // shops
  'Sales Assistant': L('blazer', BLACK, 'long', 'blond', 'a', { tie: SHIRT }),
  'Bookseller': L('cardigan', '#6a7a4a', 'curly', 'brown', 'a', { glasses: true, beard: true }),
  'Florist': L('apron', '#f2e3c4', 'long', 'ginger', 'a', { accent: '#c98a9a' }),
  'Shopkeeper': L('apron', '#4a8a7a', 'bald', 'gray', 'c', { head: 'round', accent: GOLD, old: true, mustache: true }),
  'Technician': L('polo', '#3a5ea8', 'buzz', 'black', 'b', { head: 'round', badge: WHITE, glasses: true }),
  'Specialist': L('polo', '#6e3b8f', 'sidepart', 'black', 'b', { head: 'round', badge: '#f2c14e' }),
  'Advisor': L('polo', '#2f6fb5', 'buzz', 'black', 'd', { head: 'square', badge: WHITE }),
  'Assistant': L('coat', COAT, 'bob', 'auburn', 'b', { glasses: true }),
  'Clerk': L('polo', '#5f7ec0', 'bob', 'gray', 'a', { glasses: true, old: true, badge: WHITE }),
  'Tailor': L('barvest', '#5a5048', 'bald', 'gray', 'b', { tie: '#8f2a36', glasses: true, old: true, tape: true, badge: GOLD }),
  'Cobbler': L('apron', '#8a9aa8', 'bald', 'white', 'b', { head: 'round', accent: '#6b4a2f', glasses: true, old: true }),
  'Stylist': L('apron', '#c4b2d8', 'bob', 'auburn', 'b', { accent: BLACK }),
  'Artist': L('tank', BLACK, 'buzz', 'ginger', 'a', { beard: true }),
  // desks and counters
  'Agent': L('blazer', NAVY, 'bun', 'brown', 'c', { tie: '#c8463a' }),
  'Ticket Officer': L('uniform', '#3a5a4a', 'cap', 'black', 'b', { hatColor: '#3a5a4a', badge: GOLD }),
  'Transit Officer': L('uniform', '#4a5f7a', 'cap', 'black', 'e', { head: 'square', hatColor: '#4a5f7a', badge: '#f2c14e', mustache: true }),
  'Postal Clerk': L('polo', '#4a6a8a', 'curly', 'black', 'e', { badge: '#c8463a' }),
  'Staff': L('tee', '#3aa0a0', 'cap', 'brown', 'c', { hatColor: WHITE, badge: '#3aa0a0' }),
  'Guide': L('blazer', '#7d3324', 'bun', 'gray', 'a', { tie: GOLD, glasses: true }),
  'Admissions Officer': L('cardigan', '#3a5a8a', 'bob', 'brown', 'd', { glasses: true }),
  'Librarian': L('cardigan', '#a8657e', 'bun', 'brown', 'b', { glasses: true }),
  'Curator': L('blazer', BLACK, 'bob', 'white', 'a', { tie: '#d4a64c', glasses: true }),
  'Consultant': L('polo', '#2f6f8f', 'buzz', 'black', 'd', { head: 'square', badge: WHITE }),
  'Host': L('blazer', '#7b3f8f', 'sidepart', 'blond', 'b', { tie: GOLD }),
  'Game Master': L('hoodie', '#3a3a44', 'beanie', 'black', 'c', { head: 'round', hatColor: '#7b3f8f', badge: '#5a2a6a', glasses: true }),
  'Community Manager': L('tee', '#d9b04a', 'long', 'black', 'd'),
  // health
  'Veterinarian': L('coat', COAT, 'ponytail', 'brown', 'c'),
  'Nurse Morgan': L('scrubs', '#3a8a8a', 'ponytail', 'blond', 'a'),
  // money, property, work
  'Banker': L('blazer', '#3b3f52', 'sidepart', 'gray', 'a', { head: 'square', tie: '#7d3324' }),
  'Property Manager': L('blazer', '#5a5048', 'bob', 'brown', 'c', { tie: '#3a5ea8' }),
  'Real Estate Agent': L('blazer', '#2f5a4a', 'long', 'brown', 'b', { tie: SHIRT }),
  'Interviewer': L('blazer', CHARCOAL, 'sidepart', 'brown', 'b', { tie: '#3a5ea8' }),
  'Adjuster Miller': L('blazer', '#5a5f6a', 'sidepart', 'gray', 'a', { head: 'square', tie: '#7d3324', glasses: true }),
  'Landlord Mr. Sterling': L('blazer', '#4a3a34', 'bald', 'gray', 'a', { head: 'square', tie: '#a23f3f', old: true, mustache: true }),
  'Director Henderson': L('blazer', '#26272f', 'sidepart', 'white', 'a', { head: 'square', tie: '#8f2a36', old: true }),
  'Loan Officer Arthur': L('blazer', '#3b3f52', 'sidepart', 'brown', 'c', { tie: '#3a5ea8', glasses: true, beard: true }),
  'Planner Celeste': L('blazer', '#c98a9a', 'long', 'auburn', 'a', { tie: SHIRT }),
  'Supervisor Karen': L('blazer', NAVY, 'bob', 'blond', 'a', { tie: '#c8463a' }),
  'Founder Sam': L('hoodie', '#2f6f5a', 'sidepart', 'black', 'b', { head: 'round', stubble: true }),
  'Neighbor': L('tee', '#6f9fd0', 'curly', 'brown', 'b', { head: 'round' }),
  // the law and the road
  'Duty Officer': L('uniform', NAVY, 'cap', 'brown', 'b', { head: 'square' }),
  'Officer Vance': L('uniform', '#2b2f3a', 'cap', 'blond', 'a', { head: 'square', hatColor: '#2b2f3a', stubble: true }),
  'Inspector Zhao': L('uniform', '#3a4a6a', 'cap', 'black', 'b', { head: 'square', hatColor: '#3a4a6a', glasses: true }),
  'Ranger': L('uniform', '#6b7a4a', 'ranger', 'black', 'c', { hatColor: '#a88b57', badge: '#6b4a2f' }),
  'Driver': L('polo', '#3a5ea8', 'cap', 'black', 'c', { head: 'square', hatColor: BLACK, badge: WHITE, stubble: true }),
  'Mechanic': L('overalls', '#3a5a7a', 'buzz', 'brown', 'b', { head: 'square', badge: WHITE, stubble: true }),
}

// One name, a different job: the scenario's own clothes for its speaker.
export const BY_SCENARIO: Record<string, Partial<Look>> = {
  'Car Rental Agency': { outfit: 'polo', cloth: '#2f6f5a', badge: WHITE, hair: 'ponytail' },
  'Insurance Policy Review': { cloth: '#4a4e6a', tie: '#3a5ea8', hair: 'sidepart', hairColor: 'brown' },
  'Music Concert Box Office': { outfit: 'polo', cloth: BLACK, badge: GOLD, hair: 'curly' },
  'Hospital Clinic Check-in': { outfit: 'scrubs', cloth: '#5f9ea0' },
  'Dental Clinic Checkup': { outfit: 'scrubs', cloth: '#7fb2d6' },
  'Spa & Massage Reservation': { outfit: 'polo', cloth: '#8fb8a8', badge: WHITE, hair: 'bun' },
  'Yoga Studio Class Pass': { outfit: 'tank', cloth: '#7a9a7e', hair: 'ponytail' },
  'Public Swimming Pool Pass': { outfit: 'polo', cloth: '#2f7fb5', badge: WHITE, hair: 'ponytail' },
  'Airport Lounge Access': { cloth: NAVY, tie: GOLD },
  'Ski Resort Pass & Gear': { outfit: 'hoodie', cloth: '#c0504d', hair: 'beanie', hatColor: '#2f6f8f', badge: WHITE },
  'Furniture Store Buying Sofa': { outfit: 'blazer', cloth: '#6b5a4a', tie: SHIRT },
  'Plant Nursery Advice': { outfit: 'apron', cloth: '#d8cfb4', accent: '#4d6b3d' },
  'Job Interview (Software Engineer)': { outfit: 'flannel', cloth: '#4a6a8a' },
  'Job Interview (Marketing)': { cloth: '#7b3f5a', tie: SHIRT, hair: 'bob', hairColor: 'black' },
  'Tourist Info Center': { outfit: 'polo', cloth: '#e8742a', badge: WHITE, hair: 'ponytail', hairColor: 'blond' },
  'Bowling Alley Booking': { outfit: 'polo', cloth: '#7b3f8f', badge: '#f2c14e', hair: 'sidepart' },
  'Fast Food Drive-thru': { cloth: '#c8463a', hair: 'cap', hatColor: '#c8463a', badge: '#f2c14e' },
  'Hardware Store Supplies': { outfit: 'apron', cloth: '#4a6a8a', accent: '#e8742a', old: false },
  'Music Instrument Store': { outfit: 'flannel', cloth: '#3a3a44', hair: 'long', hairColor: 'brown', glasses: false, old: false },
  'Amusement Park Tickets': { cloth: '#e2b64a', badge: '#c8463a', hair: 'cap', hatColor: '#c8463a', glasses: false, old: false },
  'Ferry Terminal Booking': { cloth: NAVY, hair: 'cap', hatColor: NAVY, glasses: false, old: false },
  'Airport Duty Free Shop': { outfit: 'blazer', cloth: BLACK, tie: SHIRT, hair: 'bun', skin: 'a', head: 'oval' },
  'Flea Market Antiques': { outfit: 'cardigan', cloth: '#8a6a4a', hair: 'bald', hairColor: 'gray', skin: 'a', old: true, glasses: true, mustache: true },
}

// Not catalogue speakers: the review chat's friend, an explain listener, and
// whoever a new scenario brings before it is drawn here.
const OTHERS: Record<string, Look> = {
  'Friend': L('hoodie', '#7d84a8', 'sidepart', 'brown', 'b'),
  'Listener': L('cardigan', '#8c5a4a', 'bun', 'gray', 'a', { glasses: true }),
}
const DEFAULT = L('blazer', '#4a4e6a', 'sidepart', 'brown', 'b', { tie: RED })

/** The speaker's look in a scenario: the speaker's own, re-dressed for the scenario's job if it has one. */
export function lookFor(speaker: string, scenario = ''): Look {
  return SPEAKERS[speaker] ? { ...SPEAKERS[speaker], ...BY_SCENARIO[scenario] } : OTHERS[speaker] ?? DEFAULT
}

export function outfitFor(speaker: string, scenario = ''): string {
  return lookFor(speaker, scenario).outfit
}

/** The face a session's mood starts from (the six NPC_MOODS in app/llm/prompts.py). */
export function expressionForMood(mood: string): Expression {
  const m = mood.toLowerCase()
  if (m.startsWith('harried')) return 'harried'
  if (m.startsWith('chatty')) return 'smile'
  if (m.startsWith('curt')) return 'curt'
  if (m.startsWith('skeptical')) return 'skeptical'
  if (m.startsWith('cheerful')) return 'grin'
  if (m.startsWith('calm')) return 'calm'
  return 'neutral'
}

/** Which of the kit's six hand-drawn faces an expression is drawn with. */
export const FACE: Record<Expression, Mood> = {
  neutral: 'neutral', calm: 'neutral',
  smile: 'smile', grin: 'smile',
  surprised: 'surprised', harried: 'surprised',   // wide-eyed, rushed off their feet
  skeptical: 'confused',
  curt: 'annoyed',
  concern: 'sad',                                 // a red mark: brows up in sympathy
}
