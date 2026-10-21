import { Bust } from './pixel/Bust'
import { MOODS } from './pixel/faces'
import { BY_SCENARIO, expressionForMood, FACE, lookFor, SPEAKERS } from './characters'
import { SCENES } from './scenes'

// Dev-only review page (/ui/gallery under `npm run dev`): every catalogue
// speaker in the pixel kit, the scenarios that re-dress one, and the six
// hand-drawn faces. Art changes are reviewed here, by screenshot, before
// they reach a screen; docs/design/pixel/speakers.md is the same list in words.

const NPC_MOODS = [
  'harried and rushing', 'chatty and friendly', 'curt and impatient',
  'skeptical and questioning', 'cheerful but scatterbrained', 'calm and unhurried',
]

const card = { display: 'flex', flexDirection: 'column' as const, alignItems: 'center', gap: 4,
  background: '#e8e0cf', borderRadius: 3, padding: '10px 6px 6px', color: '#3a3346' }
const row = { display: 'flex', flexWrap: 'wrap' as const, gap: 12, marginBottom: 28 }

/** Which catalogue speaker a scenario's re-dressing applies to. */
const speakerOf = (scenario: string) =>
  Object.keys(SPEAKERS).find((s) => lookFor(s, scenario).outfit !== SPEAKERS[s].outfit
    || JSON.stringify(lookFor(s, scenario)) !== JSON.stringify(SPEAKERS[s])) ?? ''

export function Gallery() {
  const speakers = Object.keys(SPEAKERS)
  return (
    <div style={{ fontFamily: 'var(--font-ui)', color: '#eceaf4', background: '#15161f', padding: 32, minHeight: '100vh' }}>
      <h1 style={{ margin: '0 0 6px' }}>Pixel speakers</h1>
      <p style={{ margin: '0 0 20px', color: '#a2a6c0' }}>{speakers.length} catalogue speakers · each dressed for the job</p>
      <h2>The six faces (Barista)</h2>
      <div style={row}>
        {MOODS.map((m) => (
          <div key={m} style={card}><Bust spec={{ ...lookFor('Barista'), mood: m }} scale={4} title={`Barista, ${m}`} /><b>{m}</b></div>
        ))}
      </div>
      <h2>NPC moods → starting face (Receptionist)</h2>
      <div style={row}>
        {NPC_MOODS.map((m) => (
          <div key={m} style={card}>
            <Bust spec={{ ...lookFor('Receptionist'), mood: FACE[expressionForMood(m)] }} scale={3} />
            <b style={{ fontSize: 13, maxWidth: 130, textAlign: 'center' }}>{m}</b>
          </div>
        ))}
      </div>
      <h2>All speakers</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: 12, marginBottom: 28 }}>
        {speakers.map((s) => (
          <div key={s} style={card}>
            <Bust spec={lookFor(s)} scale={3} title={s} />
            <b style={{ fontSize: 14, textAlign: 'center' }}>{s}</b>
            <span style={{ fontSize: 12 }}>{lookFor(s).outfit}</span>
          </div>
        ))}
      </div>
      <h2>Re-dressed for a scenario</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: 12 }}>
        {Object.keys(BY_SCENARIO).filter((sc) => sc in SCENES).map((sc) => (
          <div key={sc} style={card}>
            <Bust spec={lookFor(speakerOf(sc), sc)} scale={3} />
            <b style={{ fontSize: 13, textAlign: 'center' }}>{speakerOf(sc)}</b>
            <span style={{ fontSize: 12, textAlign: 'center' }}>{sc}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
