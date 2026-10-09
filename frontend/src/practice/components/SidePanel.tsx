import { useEffect, useRef } from 'react'
import { copyFor } from '../copy'
import { fill, parseCorrections, parseLevelUp, type LevelUp } from '../coach'
import type { SessionState } from '../session'

/** Tasks, the coach's corrections, and the words collected this session. */
export function SidePanel({ state }: { state: SessionState }) {
  const { str, tasks } = state
  const done = tasks.filter((t) => t.done).length
  return (
    <div id="side">
      <div className="sect" id="tasksBox">
        <h3><span id="tasksLabel">{str.web_tasks || 'Tasks'}</span>{' '}
          <span id="taskCount">{tasks.length ? `${done}/${tasks.length}` : ''}</span></h3>
        <div id="bar"><div id="barFill" style={{ width: tasks.length ? `${(100 * done) / tasks.length}%` : 0 }} /></div>
        <div id="taskScroll"><TaskList state={state} /></div>
      </div>
      <div className="sect" id="coachBox">
        <h3 id="coachLabel">{str.web_coach || copyFor(state.lang).margin}</h3>
        <Coach state={state} />
      </div>
      {/* Explain mode has no NPC teaching vocabulary, so the panel would sit
          there promising words that never arrive. The coach takes the space. */}
      <div className="sect" id="vocabBox" hidden={state.mode === 'explain'}>
        <h3 id="vocabLabel">{str.web_vocabulary || 'Vocabulary'}</h3>
        {state.words.length ? (
          <div id="vocabList">{state.words.map((w, i) => <div key={i}>• {w}</div>)}</div>
        ) : (
          <div id="vocabList" className="muted">{str.web_vocab_empty || 'New words from the conversation will appear here.'}</div>
        )}
      </div>
    </div>
  )
}

function TaskList({ state }: { state: SessionState }) {
  const current = useRef<HTMLLIElement>(null)
  useEffect(() => { current.current?.scrollIntoView?.({ block: 'nearest' }) }, [state.tasks])
  return (
    <ul id="tasks">
      {state.tasks.map((t, i) => {
        // a skipped task is not a done one: it gets its own ✗, not the green ✓
        const cls = t.skipped ? 'skipped' : t.done ? 'done' : t.current ? 'current' : 'todo'
        return (
          <li key={i} ref={t.current ? current : undefined}
              className={cls + (i === state.justDone ? ' just' : '')}>{t.goal}</li>
        )
      })}
    </ul>
  )
}

function Coach({ state }: { state: SessionState }) {
  const { coach, str } = state
  const c = copyFor(state.lang)
  const box = useRef<HTMLDivElement>(null)
  // On a phone the panel is capped at 45vh and the repeat badge is the last
  // line of its correction, so it was the first thing cut off.
  useEffect(() => {
    box.current?.querySelector('.fix .repeat')?.closest('.fix')?.scrollIntoView?.({ block: 'nearest' })
  }, [coach])

  if (!coach)
    return <div id="coach" className="muted">{str.web_coach_empty || 'Your grammar feedback will appear here after each message.'}</div>

  const levelUp = parseLevelUp(coach.text)
  if (coach.clean)
    return (
      <div id="coach" ref={box}>
        <div className="allgood"><b>{c.natural}</b></div>
        {levelUp && <LevelUpBlock lu={levelUp} label={c.levelUp} />}
      </div>
    )

  const fixes = parseCorrections(coach.text, coach.repeats)
  return (
    <div id="coach" ref={box}>
      {fixes.map((f, i) => (
        <div className="fix" key={i}>
          <span className="was">{f.was}</span>
          <span className="now">{f.now}</span>
          <span className="why">{f.why}</span>
          {f.repeats !== undefined && (
            <span className="repeat">{fill(str.web_repeat_badge || '🔁 {n}× — you’ve made this mistake before', { n: f.repeats })}</span>
          )}
        </div>
      ))}
      {levelUp && <LevelUpBlock lu={levelUp} label={c.levelUp} />}
      {/* anything unparsed still has to be shown */}
      {!fixes.length && !levelUp && <div style={{ whiteSpace: 'pre-wrap' }}>{coach.text}</div>}
    </div>
  )
}

function LevelUpBlock({ lu, label }: { lu: LevelUp; label: string }) {
  return (
    <div className="fix" style={{ borderLeftColor: 'var(--accent)', marginTop: 14 }}>
      <span className="tag">{label}</span>
      <span className="now">{lu.to}</span>
      <span className="why">{lu.why}</span>
    </div>
  )
}
