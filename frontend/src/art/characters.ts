// Who each catalogue speaker looks like. The catalogue has 58 speakers across
// 80 scenarios; each maps to one of a dozen outfit archetypes by role, and
// everything else (skin, hair, glasses) is drawn deterministically from the
// speaker's name, so the same barista looks the same every session.

export type Outfit =
  | 'apron' | 'whitecoat' | 'uniform' | 'suit' | 'blazer' | 'vest' | 'overalls'
  | 'ranger' | 'hoodie' | 'smock' | 'chef' | 'tailor' | 'cardigan' | 'tee'

export type Hair = 'short' | 'bun' | 'long' | 'bob' | 'curly' | 'buzz' | 'bald' | 'ponytail'

export type Expression =
  | 'neutral' | 'smile' | 'grin' | 'calm' | 'curt' | 'skeptical' | 'harried' | 'concern' | 'surprised'

export interface Look {
  outfit: Outfit
  hair: Hair
  hairColor: string
  skin: string
  glasses: boolean
  beard: boolean
  accent: string          // the outfit's main colour
}

// Role words, matched against the speaker name ("Loan Officer Arthur" is an
// officer of the suit kind, not the police kind — so longer keys go first).
const OUTFIT_BY_ROLE: [string, Outfit][] = [
  ['loan officer', 'suit'], ['admissions officer', 'blazer'], ['ticket officer', 'blazer'],
  ['transit officer', 'uniform'], ['duty officer', 'uniform'], ['officer', 'uniform'],
  ['inspector', 'uniform'], ['scoop staff', 'apron'], ['sales assistant', 'blazer'],
  ['real estate', 'suit'], ['property manager', 'suit'], ['community manager', 'tee'],
  ['chef', 'chef'], ['game master', 'hoodie'], ['postal clerk', 'blazer'],
  ['barista', 'apron'], ['baker', 'apron'], ['florist', 'apron'], ['farmer', 'overalls'],
  ['vendor', 'apron'], ['shopkeeper', 'apron'], ['cobbler', 'apron'], ['cashier', 'apron'],
  ['pharmacist', 'whitecoat'], ['veterinarian', 'whitecoat'], ['nurse', 'whitecoat'],
  ['specialist', 'whitecoat'], ['technician', 'overalls'], ['mechanic', 'overalls'],
  ['banker', 'suit'], ['interviewer', 'suit'], ['director', 'suit'], ['consultant', 'suit'],
  ['advisor', 'suit'], ['adjuster', 'suit'], ['landlord', 'suit'], ['agent', 'blazer'],
  ['receptionist', 'blazer'], ['clerk', 'blazer'], ['staff', 'blazer'], ['host', 'blazer'],
  ['librarian', 'cardigan'], ['curator', 'cardigan'], ['bookseller', 'cardigan'],
  ['waiter', 'vest'], ['sommelier', 'vest'], ['ranger', 'ranger'], ['guide', 'ranger'],
  ['founder', 'hoodie'], ['artist', 'smock'], ['stylist', 'smock'], ['tailor', 'tailor'],
  ['planner', 'blazer'], ['supervisor', 'blazer'], ['assistant', 'blazer'],
  ['driver', 'tee'], ['neighbor', 'tee'],
]

const ACCENT: Record<Outfit, string> = {
  apron: '#2F4858', whitecoat: '#BFD4E6', uniform: '#24345A', suit: '#2B2F3A',
  blazer: '#3E5C8A', vest: '#F3EFE4', overalls: '#4F6D7A', ranger: '#A88B57',
  hoodie: '#6B7F5E', smock: '#E7D3B0', chef: '#FFFFFF', tailor: '#F3EFE4',
  cardigan: '#8C5A4A', tee: '#C66B4E',
}

const SKINS = ['#F6DCC6', '#EBC3A0', '#D7A07A', '#AD7651', '#7E5236']
const HAIR_COLORS = ['#2B1D16', '#3B2A20', '#6B4A2E', '#A7703F', '#C9B79C', '#1F1F24']
const HAIRS: Hair[] = ['short', 'bun', 'long', 'bob', 'curly', 'buzz', 'ponytail', 'short', 'bald']

/** A stable 32-bit hash (FNV-1a), so a speaker's look never changes. */
function hash(text: string): number {
  let h = 0x811c9dc5
  for (const ch of text) {
    h ^= ch.codePointAt(0)!
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return h
}

export function outfitFor(speaker: string): Outfit {
  const s = speaker.toLowerCase()
  return OUTFIT_BY_ROLE.find(([role]) => s.includes(role))?.[1] ?? 'blazer'
}

export function lookFor(speaker: string): Look {
  const h = hash(speaker)
  const outfit = outfitFor(speaker)
  const hair = HAIRS[h % HAIRS.length]
  return {
    outfit,
    hair,
    hairColor: HAIR_COLORS[(h >>> 4) % HAIR_COLORS.length],
    skin: SKINS[(h >>> 8) % SKINS.length],
    glasses: outfit === 'cardigan' || (h >>> 12) % 5 === 0,
    beard: (hair === 'bald' || hair === 'buzz' || hair === 'short') && (h >>> 16) % 3 === 0,
    accent: ACCENT[outfit],
  }
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
