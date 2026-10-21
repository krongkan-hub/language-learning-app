import { useEffect, useRef, type ReactNode } from 'react'
import { copyFor } from '../copy'
import { fill, parseCorrections, parseLevelUp, type LevelUp } from '../coach'
import type { SessionState } from '../session'

/**
 * The coach's verdict on the learner's last line, as a ticket stub on the
 * postcard (#62): each red mark wrong → right with its reason, the retype
 * box under it while the drill holds the learner, and a FIX stamp on the
 * stub with the red mark's number this page. A mistake made before says
 * which time it is in the label. A clean line gets a short teal ticket
 * instead. The next line sent clears it (session.ts 'sent').
 */
export function RedMarkCard({ state, drill }: { state: SessionState; drill: ReactNode }) {
  const { coach, str } = state
  const c = copyFor(state.lang)
  const box = useRef<HTMLDivElement>(null)
  // A phone caps the stub's height, and the repeat badge is the last line of
  // its correction, so it was the first thing cut off.
  useEffect(() => {
    box.current?.querySelector('.fix .repeat')?.closest('.fix')?.scrollIntoView?.({ block: 'nearest' })
  }, [coach])

  if (!coach && !drill) return null
  const levelUp = coach ? parseLevelUp(coach.text) : null

  if (coach?.clean && !drill)
    return (
      <div id="coachBox" className="tix clean" ref={box}>
        <div id="coach">
          <div className="allgood"><b>{c.natural}</b></div>
          {levelUp && <LevelUpBlock lu={levelUp} label={c.levelUp} />}
        </div>
      </div>
    )

  const fixes = coach ? parseCorrections(coach.text, coach.repeats) : []
  const times = Math.max(0, ...fixes.map((f) => f.repeats ?? 0))
  return (
    <div id="coachBox" className="tix stub" ref={box}>
      <div className="main">
        <h3 id="coachLabel" className="lbl pen">{str.web_coach || 'Red mark'}{times > 1 ? ` · ${c.card.nth(times)}` : ''}</h3>
        <div id="coach">
          {fixes.map((f, i) => (
            <div className="fix" key={i}>
              <span className="was">{f.was}</span>
              <span className="arrow" aria-hidden="true">→</span>
              <span className="now">{f.now}</span>
              <span className="why">{f.why}</span>
              {f.repeats !== undefined && (
                <span className="repeat">{fill(str.web_repeat_badge || '🔁 {n}× — you’ve made this mistake before', { n: f.repeats })}</span>
              )}
            </div>
          ))}
          {levelUp && <LevelUpBlock lu={levelUp} label={c.levelUp} />}
          {/* anything unparsed still has to be shown */}
          {coach && !fixes.length && !levelUp && <div style={{ whiteSpace: 'pre-wrap' }}>{coach.text}</div>}
        </div>
        {drill}
      </div>
      <div className="s" aria-hidden="true">
        <span className="stamp">{c.card.stamp}</span>
        <span>{c.card.no(Math.max(1, state.fixes.length))}</span>
      </div>
    </div>
  )
}

function LevelUpBlock({ lu, label }: { lu: LevelUp; label: string }) {
  return (
    <div className="fix levelUp">
      <span className="tag">{label}</span>
      <span className="now">{lu.to}</span>
      <span className="why">{lu.why}</span>
    </div>
  )
}
