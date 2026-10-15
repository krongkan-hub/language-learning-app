import type { Ref } from 'react'
import { Reward } from '../../art/Reward'
import { copyFor } from '../copy'
import type { SessionState } from '../session'
import { levelOf, plus, sessionTotals, xpOf, type Totals } from '../xp'

interface Props {
  state: SessionState
  totals: Totals
  streak: number
  endRef: Ref<HTMLButtonElement>
  onSkip: () => void
  onEnd: () => void
}

/**
 * The HUD (#62): level and XP, the streak, this page's rewards, the place and
 * the speaker, and the two controls. One row that never grows: everything
 * truncates, the two buttons never shrink (see practice.css).
 */
export function Header({ state, totals, streak, endRef, onSkip, onEnd }: Props) {
  const { header, str } = state
  const c = copyFor(state.lang)
  const { level, into, span } = levelOf(xpOf(plus(totals, sessionTotals(state))))
  return (
    <header id="hud">
      <div className="hudLevel">
        <span className="lv pixel">{c.hud.level(level)}</span>
        <div className="xpbar" role="progressbar" aria-label={c.hud.xpName} aria-valuemin={0}
             aria-valuemax={span} aria-valuenow={into} aria-valuetext={c.hud.xp(into, span)}>
          <i style={{ width: `${(100 * into) / span}%` }} />
        </div>
        <span className="xptext pixel" aria-hidden="true">{c.hud.xp(into, span)}</span>
      </div>
      <b id="hScenario">{header.scenario}</b>
      <div id="hMeta">
        {/* an explain topic's "place" is its title again: said once is enough */}
        <span id="hPlace">{header.place !== header.scenario ? header.place : ''}</span>
        <span id="hSpeaker">{header.speaker}</span>
        <span id="hMood" style={{ fontStyle: 'italic' }}>{header.mood}</span>
      </div>
      <span className="hudStat" title={c.hud.streak(streak)}>
        <span aria-hidden="true">🔥</span><b aria-hidden="true">{streak}</b>
        <span className="sr-only">{c.hud.streak(streak)}</span>
      </span>
      <span className="hudStat" title={c.hud.rewards(state.hanamaru)}>
        <Reward icon={c.reward.icon} size={22} /><b aria-hidden="true">×{state.hanamaru}</b>
        <span className="sr-only">{c.hud.rewards(state.hanamaru)}</span>
      </span>
      <button className="ghost" id="skipBtn" onClick={onSkip}>{str.web_skip_task || 'Skip task'}</button>
      <button className="ghost" id="endBtn" onClick={onEnd} ref={endRef}>{str.web_end || 'End'}</button>
    </header>
  )
}
