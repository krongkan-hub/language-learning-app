import type { Ref } from 'react'
import { PixelIcon, Reward } from '../../art/Reward'
import { copyFor } from '../copy'
import type { SessionState } from '../session'
import type { Language } from '../types'
import { levelOf, plus, sessionTotals, xpOf, type Totals } from '../xp'

interface Props {
  state: SessionState
  totals: Totals
  streak: number
  endRef: Ref<HTMLButtonElement>
  onSkip: () => void
  onEnd: () => void
}

const SEGMENTS = 8

/** The level tag and the XP tag with its bar: the HUD's, and Today's player ticket's. */
export function LevelTags({ lang, xp }: { lang: Language; xp: number }) {
  const c = copyFor(lang)
  const { level, into, span } = levelOf(xp)
  const lit = Math.round((SEGMENTS * into) / span)
  return (
    <>
      <span className="tag lv">{c.hud.level(level)}</span>
      <span className="tag mint xp" role="progressbar" aria-label={c.hud.xpName} aria-valuemin={0}
            aria-valuemax={span} aria-valuenow={into} aria-valuetext={c.hud.xp(into, span)}>
        <span aria-hidden="true">{c.hud.xp(into, span)}</span>
        <span className="bar" aria-hidden="true">
          {Array.from({ length: SEGMENTS }, (_, i) => <i key={i} className={i < lit ? 'on' : ''} />)}
        </span>
      </span>
    </>
  )
}

/**
 * The HUD as luggage tags (#62): level, XP, the streak, this page's
 * rewards, the trip (scenario), and the two controls. One row that never
 * grows: the trip tag truncates, the buttons never shrink (practice.css).
 * The place, speaker and mood are here for a screen reader; sighted, they
 * are on the postcard's NOW AT tag.
 */
export function Header({ state, totals, streak, endRef, onSkip, onEnd }: Props) {
  const { header, str } = state
  const c = copyFor(state.lang)
  return (
    <header id="hud">
      <LevelTags lang={state.lang} xp={xpOf(plus(totals, sessionTotals(state)))} />
      <span className="tag paper hudStat" title={c.hud.streak(streak)}>
        <PixelIcon kind="fire" size={20} /><span aria-hidden="true">{c.hud.days(streak)}</span>
        <span className="sr-only">{c.hud.streak(streak)}</span>
      </span>
      <span className="tag paper hudStat" title={c.hud.rewards(state.hanamaru)}>
        <Reward icon={c.reward.icon} size={20} /><span aria-hidden="true">×{state.hanamaru}</span>
        <span className="sr-only">{c.hud.rewards(state.hanamaru)}</span>
      </span>
      <span className="tag paper trip">
        <span aria-hidden="true">{c.hud.trip} · </span><b id="hScenario">{header.scenario}</b>
        <span id="hMeta" className="sr-only">
          {/* an explain topic's "place" is its title again: said once is enough */}
          <span id="hPlace">{header.place !== header.scenario ? header.place : ''}</span>{' '}
          <span id="hSpeaker">{header.speaker}</span>{' '}
          <span id="hMood">{header.mood}</span>
        </span>
      </span>
      <button className="btn ghost" id="skipBtn" onClick={onSkip}>{str.web_skip_task || 'Skip task'}</button>
      <button className="btn ghost" id="endBtn" onClick={onEnd} ref={endRef}>{str.web_end || 'End'}</button>
    </header>
  )
}
