import { useEffect, useState } from 'react'
import { Cafe } from '../../art/pixel/Cafe'
import { useBust, Bust } from '../../art/pixel/Bust'
import type { KitSpec } from '../../art/pixel/render'
import { Scene } from '../../art/Scene'
import { expressionForMood, FACE, lookFor, type Expression } from '../../art/characters'
import { isCafe, sceneFor } from '../../art/scenes'
import { copyFor } from '../copy'
import type { SessionState } from '../session'

const ART_W = 208, ART_H = 112

/**
 * Art pixels per CSS pixel: a whole number, so every pixel is the same
 * size, from what the window leaves the postcard beside the side tickets
 * and above the dialogue ticket. 5 at 1440x900 (1040x560, the mockup's).
 */
function pick(): number {
  const byWidth = Math.floor((window.innerWidth - 400) / ART_W)
  const byHeight = Math.floor((window.innerHeight - 340) / ART_H)
  return Math.max(2, Math.min(5, byWidth, byHeight))
}

export function useStageScale(): number {
  const [k, setK] = useState(pick)
  useEffect(() => {
    const on = () => setK(pick())
    window.addEventListener('resize', on)
    return () => window.removeEventListener('resize', on)
  }, [])
  return k
}

/** The face the speaker wears: the session's mood, or a reaction to the learner's last line. */
export function expressionOf(state: SessionState): Expression {
  if (state.reaction === 'fixed') return 'grin'
  if (state.reaction === 'mistake') return 'concern'
  return expressionForMood(state.art?.mood ?? '')
}

/** The speaker drawn with the kit: dressed for the scenario's job, wearing the face. */
export function speakerSpec(state: SessionState): KitSpec {
  const art = state.art!
  return { ...lookFor(art.speaker, art.scenario), mood: FACE[expressionOf(state)] }
}

/**
 * The place and the person the learner is talking to (#50a), as a postcard
 * (#62): the café is the pixel scene (docs/design/pixel/scene-cafe.js) with
 * the speaker drawn into it; the other scenes are still the older drawings
 * (art/Scene.tsx), with the pixel speaker standing in front, until they are
 * redrawn. The NOW AT tag names the place and the speaker. Decorative: the
 * HUD says the same to a screen reader.
 */
export function Stage({ state, scale }: { state: SessionState; scale: number }) {
  if (!state.art) return null
  return <StageArt state={state} scale={scale} />
}

function StageArt({ state, scale }: { state: SessionState; scale: number }) {
  const { header, lang } = state
  const spec = speakerSpec(state)
  const who = useBust(spec)
  const scene = sceneFor(state.art!.scenario)
  const cafe = isCafe(state.art!.scenario)
  return (
    <div id="stage" aria-hidden="true" data-scene={cafe ? 'cafe' : scene.template} data-expression={expressionOf(state)}
         style={{ width: ART_W * scale, height: ART_H * scale }}>
      {cafe ? <Cafe who={who} scale={scale} /> : (
        <>
          <Scene spec={scene} language={lang} height={ART_H * scale} />
          <div className="stage-speaker" data-expression={expressionOf(state)} style={{ left: 34 * scale }}>
            <Bust spec={spec} scale={scale} />
          </div>
        </>
      )}
      <div className="tix where">
        <div className="lbl">{copyFor(lang).postcard.nowAt}</div>
        <b>{header.place || header.scenario}</b> · <span>{header.speaker}</span>
        {header.mood && <div className="mood">{header.mood.replace(/^· /, '')}</div>}
      </div>
    </div>
  )
}
