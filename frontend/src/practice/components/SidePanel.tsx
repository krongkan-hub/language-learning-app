import { useEffect, useRef } from 'react'
import { Sprite } from '../../art/pixel/Sprite'
import type { Today } from '../api'
import { copyFor } from '../copy'
import type { SessionState } from '../session'
import type { Totals } from '../xp'

// The mockup's sprites (docs/design/pixel/pixel-mockup-v4.html).
const BAG = ['....oooooo......', '...o......o.....', '...o......o.....', '.oooooooooooo...', '.okkkkkkkkkko...',
  '.okkkkkkkkkko...', '.okkkkGGkkkko...', '.okkkkkkkkkko...', '.okkkkkkkkkko...', '.oooooooooooo...']
const BAG_PAL = { o: '#5c3b1f', k: '#c9a06b', G: '#7fae5f' }
const SLIME = ['........oo........', '......oorroo......', '.....orrrrrro.....', '....orRRrrrrro....', '...orRRrrrrrrro...',
  '..orrwwrrrwwrrro..', '..orrwkrrrwkrrro..', '.orrrrrrrrrrrrrro.', '.orrrrrkkkkrrrrro.', 'orrrrrrrrrrrrrrrro',
  'orrrrrrrrrrrrrrrro', '.oooooooooooooooo.']
const SLIME_PAL = { o: '#5e1c16', r: '#e8573f', R: '#f58a6f', w: '#fff', k: '#3a120e' }
const STAMP_INK = ['#e8573f', '#1f7a6a', '#c99628', '#3a5ea8']
const STAMPS_SHOWN = 12

/**
 * The side tickets (#62): the itinerary (the tasks), luggage tags (the
 * words collected this session; the newest is yellow), customs (the old red
 * marks still due on Today's page; each one retired is cleared for good),
 * and the passport (a stamp per place visited).
 */
export function SidePanel({ state, today, totals }: { state: SessionState; today: Today | null; totals: Totals }) {
  const { str, tasks } = state
  const done = tasks.filter((t) => t.done).length
  return (
    <div id="side">
      <section className="tix" id="tasksBox" aria-labelledby="tasksLabel">
        <h3 className="lbl"><span id="tasksLabel">{str.web_tasks || 'Itinerary'}</span>
          <span id="taskCount">{tasks.length ? ` · ${done}/${tasks.length}` : ''}</span></h3>
        <div id="taskScroll"><TaskList state={state} /></div>
      </section>
      {/* Explain mode has no NPC teaching vocabulary, so the ticket would sit
          there promising words that never arrive. */}
      <section className="tix" id="vocabBox" aria-labelledby="vocabLabel" hidden={state.mode === 'explain'}>
        <h3 id="vocabLabel" className="lbl">{str.web_vocabulary || 'Luggage · new words'}</h3>
        {state.words.length ? <Luggage state={state} /> : (
          <div id="vocabList" className="muted">{str.web_vocab_empty || 'New words from the conversation are tagged and packed here.'}</div>
        )}
      </section>
      <Customs state={state} due={today?.review.length ?? 0} retired={totals.retired} />
      <Passport state={state} places={today?.totals?.places ?? 0} />
    </div>
  )
}

function TaskList({ state }: { state: SessionState }) {
  const current = useRef<HTMLLIElement>(null)
  useEffect(() => { current.current?.scrollIntoView?.({ block: 'nearest' }) }, [state.tasks])
  return (
    <ul id="tasks">
      {state.tasks.map((t, i) => {
        // a skipped task is not a done one: it gets its own ✗, not the ✓
        const cls = t.skipped ? 'skipped' : t.done ? 'done' : t.current ? 'current' : 'todo'
        return (
          <li key={i} ref={t.current ? current : undefined}
              className={cls + (i === state.justDone ? ' just' : '')}><span className="box" aria-hidden="true" />{t.goal}</li>
        )
      })}
    </ul>
  )
}

/** A tag per word, with what the NPC said it means (the vocab card in the transcript). */
function Luggage({ state }: { state: SessionState }) {
  const meaning = (w: string) => {
    const card = state.log.find((l) => l.kind === 'vocab' && l.word === w)
    return card && card.kind === 'vocab' ? card.explanation : ''
  }
  const last = state.words.length - 1
  return (
    <ul id="vocabList" className="vtags">
      {state.words.map((w, i) => (
        <li key={i} className={'vtag' + (i === last ? ' new' : '')}>
          <Sprite rows={BAG} pal={BAG_PAL} scale={1.75} />
          <div><b>{w}</b>{meaning(w) && <span>{meaning(w)}</span>}</div>
        </li>
      ))}
    </ul>
  )
}

function Customs({ state, due, retired }: { state: SessionState; due: number; retired: number }) {
  const s = copyFor(state.lang).side
  const all = due + retired
  const clear = all > 0 && due === 0
  return (
    <section className="tix stub" id="bossBox" aria-labelledby="bossLabel">
      <div className="main">
        <h3 id="bossLabel" className="lbl pen">{s.customs}</h3>
        {all === 0 ? <p className="muted">{s.none}</p> : (
          <div className="boss">
            {!clear && <Sprite rows={SLIME} pal={SLIME_PAL} scale={3.5} className="slime" />}
            <div>
              <p>{clear ? s.allClear : s.left(due)}</p>
              <div className="hp" role="progressbar" aria-label={s.hp} aria-valuemin={0} aria-valuemax={all} aria-valuenow={due}>
                {Array.from({ length: Math.min(all, 12) }, (_, i) =>
                  <i key={i} className={i < Math.round((Math.min(all, 12) * due) / all) ? 'on' : ''} />)}
              </div>
              {retired > 0 && <p className="muted small">{s.cleared(retired)}</p>}
            </div>
          </div>
        )}
      </div>
      <div className="s" aria-hidden="true"><span className="stamp">{clear ? s.done : s.ask}</span></div>
    </section>
  )
}

function Passport({ state, places }: { state: SessionState; places: number }) {
  const s = copyFor(state.lang).side
  const shown = Math.min(places, STAMPS_SHOWN)
  return (
    <section className="tix passport" aria-labelledby="passportLabel">
      <h3 id="passportLabel" className="lbl">{s.passport(places)}</h3>
      {places === 0 ? <p className="muted small">{s.noStamps}</p> : (
        <div className="stamps" role="img" aria-label={s.stamps(places)}>
          {Array.from({ length: shown }, (_, i) => <PassportStamp key={i} ink={STAMP_INK[i % STAMP_INK.length]} tilt={i % 2} />)}
        </div>
      )}
    </section>
  )
}

/** One stamp: a square frame round a ring, the mockup's 10x10. */
function PassportStamp({ ink, tilt }: { ink: string; tilt: number }) {
  return (
    <svg width={40} height={40} viewBox="0 0 10 10" shapeRendering="crispEdges" aria-hidden="true"
         style={{ marginTop: tilt * 12 }}>
      <path d="M0 0h10v1H0zM0 9h10v1H0zM0 1h1v8H0zM9 1h1v8H9zM3 3h4v1H3zM3 6h4v1H3zM3 4h1v2H3zM6 4h1v2H6z" fill={ink} />
    </svg>
  )
}
