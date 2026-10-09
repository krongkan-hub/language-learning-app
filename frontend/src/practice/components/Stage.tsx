import { Character } from '../../art/Character'
import { Scene } from '../../art/Scene'
import { expressionForMood, lookFor, type Expression } from '../../art/characters'
import { sceneFor } from '../../art/scenes'
import type { SessionState } from '../session'

/**
 * The place and the person the learner is talking to, above the
 * conversation (#50a). The face starts on the session's mood and reacts:
 * concern at a red mark, a grin when the correction is retyped right, back
 * to the mood face on the next line. Decorative: the speaker's name and mood
 * are already in the header for a screen reader.
 */
export function Stage({ state }: { state: SessionState }) {
  const { art, reaction, lang } = state
  if (!art) return null
  const expression: Expression = reaction === 'fixed' ? 'grin'
    : reaction === 'mistake' ? 'concern'
    : expressionForMood(art.mood)
  return (
    <div id="stage" aria-hidden="true">
      <Scene spec={sceneFor(art.scenario)} language={lang} height={200} />
      <div className="stage-speaker" data-expression={expression}>
        <Character look={lookFor(art.speaker)} expression={expression} size={150} />
      </div>
      <div className="stage-plate">
        <b>{state.header.speaker}</b>
        {state.header.mood && <span>{state.header.mood.replace(/^· /, '')}</span>}
      </div>
    </div>
  )
}
