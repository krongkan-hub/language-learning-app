import { useEffect, useState } from 'react'
import { Character } from '../../art/Character'
import { Scene } from '../../art/Scene'
import { expressionForMood, lookFor, type Expression } from '../../art/characters'
import { sceneFor } from '../../art/scenes'
import type { SessionState } from '../session'

/** The stage fills the column above the dialogue box: 46% of the window, within reason. */
function useStageHeight(): number {
  const pick = () => Math.round(Math.min(460, Math.max(240, window.innerHeight * 0.46)))
  const [h, setH] = useState(pick)
  useEffect(() => {
    const on = () => setH(pick())
    window.addEventListener('resize', on)
    return () => window.removeEventListener('resize', on)
  }, [])
  return h
}

/**
 * The place and the person the learner is talking to (#50a), full-bleed
 * behind the dialogue box (#62). The face starts on the session's mood and
 * reacts: concern at a red mark, a grin when the correction is retyped right,
 * back to the mood face on the next line; the emote over the speaker's head
 * says the same at a glance. Decorative: the speaker's name and mood are
 * already in the HUD for a screen reader.
 */
export function Stage({ state }: { state: SessionState }) {
  const height = useStageHeight()
  const { art, reaction, lang } = state
  if (!art) return null
  const expression: Expression = reaction === 'fixed' ? 'grin'
    : reaction === 'mistake' ? 'concern'
    : expressionForMood(art.mood)
  const emote = state.thinking ? '…' : reaction === 'mistake' ? '❗' : reaction === 'fixed' ? '✨' : '♪'
  const size = Math.round(height * 0.78)
  return (
    <div id="stage" aria-hidden="true" style={{ height }}>
      <Scene spec={sceneFor(art.scenario)} language={lang} height={height} />
      <div className="stage-speaker" data-expression={expression}>
        <span className="emote" key={emote}>{emote}</span>
        <Character look={lookFor(art.speaker)} expression={expression} size={size} />
      </div>
      <div className="stage-plate">
        <b>{state.header.speaker}</b>
        {state.header.mood && <span>{state.header.mood.replace(/^· /, '')}</span>}
      </div>
    </div>
  )
}
