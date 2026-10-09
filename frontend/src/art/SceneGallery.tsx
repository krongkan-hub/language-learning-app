import { Scene } from './Scene'
import { SCENES } from './scenes'

// Dev-only review page (/ui/scenes under `npm run dev`): all 80 backdrops,
// each at the width the conversation column gives it, in the language chosen.

export function SceneGallery() {
  const language = new URLSearchParams(window.location.search).get('lang') === 'ja' ? 'Japanese' : 'English'
  return (
    <div style={{ fontFamily: 'Nunito, sans-serif', color: '#1B2333', background: '#FFFDF6', padding: 24 }}>
      <h1 style={{ margin: '0 0 16px' }}>Scene kit · {Object.keys(SCENES).length} scenarios · {language}</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))', gap: 14 }}>
        {Object.entries(SCENES).map(([name, spec]) => (
          <figure key={name} style={{ margin: 0, border: '2px solid #1B2333', background: '#FFFFFF' }}>
            <Scene spec={spec} language={language} height={150} />
            <figcaption style={{ fontSize: 13, fontWeight: 800, padding: '4px 8px' }}>{name} · {spec.template}</figcaption>
          </figure>
        ))}
      </div>
    </div>
  )
}
