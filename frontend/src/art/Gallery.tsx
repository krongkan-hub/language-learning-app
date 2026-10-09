import { Character } from './Character'
import { expressionForMood, lookFor, type Expression } from './characters'

// Dev-only review page (/ui/gallery under `npm run dev`): every catalogue
// speaker, and every expression on one face. Art changes are reviewed here,
// by screenshot, before they reach a screen.

const SPEAKERS = [
  'Receptionist', 'Clerk', 'Agent', 'Consultant', 'Technician', 'Interviewer', 'Guide', 'Staff',
  'Cashier', 'Advisor', 'Vendor', 'Waiter', 'Barista', 'Pharmacist', 'Officer', 'Sales Assistant',
  'Ticket Officer', 'Banker', 'Property Manager', 'Bookseller', 'Stylist', 'Driver', 'Farmer',
  'Veterinarian', 'Baker', 'Postal Clerk', 'Duty Officer', 'Shopkeeper', 'Specialist',
  'Admissions Officer', 'Librarian', 'Florist', 'Scoop Staff', 'Sommelier', 'Ranger', 'Curator',
  'Tailor', 'Real Estate Agent', 'Mechanic', 'Assistant', 'Transit Officer', 'Game Master', 'Host',
  'Artist', 'Chef Instructor', 'Cobbler', 'Community Manager', 'Neighbor', 'Nurse Morgan',
  'Supervisor Karen', 'Adjuster Miller', 'Founder Sam', 'Officer Vance', 'Landlord Mr. Sterling',
  'Inspector Zhao', 'Director Henderson', 'Loan Officer Arthur', 'Planner Celeste',
]

const EXPRESSIONS: Expression[] = [
  'neutral', 'smile', 'grin', 'calm', 'curt', 'skeptical', 'harried', 'concern', 'surprised',
]

const MOODS = [
  'harried and rushing', 'chatty and friendly', 'curt and impatient',
  'skeptical and questioning', 'cheerful but scatterbrained', 'calm and unhurried',
]

const card = { display: 'flex', flexDirection: 'column' as const, alignItems: 'center', gap: 4,
  background: '#FFFFFF', border: '1px solid #E2E9F4', borderRadius: 6, padding: '10px 6px' }

export function Gallery() {
  return (
    <div style={{ fontFamily: 'Nunito, sans-serif', color: '#1B2333', background: '#FFFDF6', padding: 32 }}>
      <h1 style={{ margin: '0 0 6px' }}>Character kit</h1>
      <p style={{ margin: '0 0 20px', color: '#5D6677' }}>{SPEAKERS.length} speakers · each look is fixed by the speaker's name</p>
      <h2>Expressions (Barista)</h2>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 28 }}>
        {EXPRESSIONS.map((e) => (
          <div key={e} style={card}>
            <Character look={lookFor('Barista')} expression={e} size={110} title={`Barista, ${e}`} />
            <b style={{ fontSize: 13 }}>{e}</b>
          </div>
        ))}
      </div>
      <h2>Moods → starting face (Receptionist)</h2>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 28 }}>
        {MOODS.map((m) => (
          <div key={m} style={card}>
            <Character look={lookFor('Receptionist')} expression={expressionForMood(m)} size={110} />
            <b style={{ fontSize: 12, maxWidth: 120, textAlign: 'center' }}>{m}</b>
          </div>
        ))}
      </div>
      <h2>All speakers</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 12 }}>
        {SPEAKERS.map((s) => (
          <div key={s} style={card}>
            <Character look={lookFor(s)} expression="smile" size={100} title={s} />
            <b style={{ fontSize: 12, textAlign: 'center' }}>{s}</b>
            <span style={{ fontSize: 11, color: '#5D6677' }}>{lookFor(s).outfit}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
