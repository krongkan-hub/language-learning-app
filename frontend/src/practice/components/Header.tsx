import type { Ref } from 'react'
import type { SessionState } from '../session'

interface Props {
  state: SessionState
  endRef: Ref<HTMLButtonElement>
  onSkip: () => void
  onEnd: () => void
}

/** One row that never grows: everything truncates, the two buttons never shrink (see practice.css). */
export function Header({ state, endRef, onSkip, onEnd }: Props) {
  const { header, str } = state
  const small = { padding: '5px 11px', fontSize: 13 }
  return (
    <header>
      <b id="hScenario">{header.scenario}</b>
      <div id="hMeta">
        <span id="hPlace">{header.place}</span>
        <span id="hSpeaker">{header.speaker}</span>
        <span id="hMood" style={{ fontStyle: 'italic' }}>{header.mood}</span>
      </div>
      <button className="ghost" id="skipBtn" style={small} onClick={onSkip}>{str.web_skip_task || 'Skip task'}</button>
      <button className="ghost" id="endBtn" style={small} onClick={onEnd} ref={endRef}>{str.web_end || 'End'}</button>
    </header>
  )
}
