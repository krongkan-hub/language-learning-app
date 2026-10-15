import { useEffect, useRef } from 'react'
import type { Today } from '../api'
import { copyFor } from '../copy'
import type { SessionState } from '../session'
import type { Totals } from '../xp'

/**
 * The side panel (#62): Quests (the tasks), Loot (the words collected this
 * session, as cards) and the Boss (the old red marks still due on Today's
 * page; each one retired is beaten for good).
 */
export function SidePanel({ state, today, totals }: { state: SessionState; today: Today | null; totals: Totals }) {
  const { str, tasks } = state
  const done = tasks.filter((t) => t.done).length
  return (
    <div id="side">
      <section className="sect" id="tasksBox" aria-labelledby="tasksLabel">
        <h3><span id="tasksLabel" className="pixel">{str.web_tasks || 'Quests'}</span>{' '}
          <span id="taskCount">{tasks.length ? `${done}/${tasks.length}` : ''}</span></h3>
        <div id="bar"><div id="barFill" style={{ width: tasks.length ? `${(100 * done) / tasks.length}%` : 0 }} /></div>
        <div id="taskScroll"><TaskList state={state} /></div>
      </section>
      {/* Explain mode has no NPC teaching vocabulary, so the panel would sit
          there promising words that never arrive. */}
      <section className="sect" id="vocabBox" aria-labelledby="vocabLabel" hidden={state.mode === 'explain'}>
        <h3 id="vocabLabel" className="pixel">{str.web_vocabulary || 'Loot'}</h3>
        {state.words.length ? <Loot state={state} /> : (
          <div id="vocabList" className="muted">{str.web_vocab_empty || 'New words from the conversation drop here as cards.'}</div>
        )}
      </section>
      <Boss state={state} due={today?.review.length ?? 0} retired={totals.retired} />
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

/** One card per word, with what the NPC said it means (the vocab card in the transcript). */
function Loot({ state }: { state: SessionState }) {
  const meaning = (w: string) => {
    const card = state.log.find((l) => l.kind === 'vocab' && l.word === w)
    return card && card.kind === 'vocab' ? card.explanation : ''
  }
  return (
    <ul id="vocabList" className="loot">
      {state.words.map((w, i) => (
        <li key={i}><b>{w}</b>{meaning(w) && <span>{meaning(w)}</span>}</li>
      ))}
    </ul>
  )
}

function Boss({ state, due, retired }: { state: SessionState; due: number; retired: number }) {
  const s = copyFor(state.lang).side
  const all = due + retired
  const open = all > 0 && due === 0
  return (
    <section className="sect" id="bossBox" aria-labelledby="bossLabel">
      <h3 id="bossLabel" className="pixel">{s.boss}</h3>
      {all === 0 ? <p className="muted">{s.bossNone}</p> : (
        <>
          <div className="hp" role="progressbar" aria-label={s.hp} aria-valuemin={0} aria-valuemax={all} aria-valuenow={due}>
            <i style={{ width: `${(100 * due) / all}%` }} />
          </div>
          <div className="bossRow">
            <Chest open={open} label={s.chest} />
            <p>{open ? s.bossClear : s.bossLeft(due)}{retired > 0 && !open && <><br /><span className="muted">{s.bossBeaten(retired)}</span></>}</p>
          </div>
        </>
      )}
    </section>
  )
}

function Chest({ open, label }: { open: boolean; label: string }) {
  return (
    <svg width="44" height="40" viewBox="0 0 44 40" role="img" aria-label={label} className={open ? 'chest open' : 'chest'}>
      <rect x="4" y="18" width="36" height="19" rx="3" fill="#b86b2e" stroke="var(--shadow)" strokeWidth="2.5" />
      {open
        ? <path d="M4 18 L8 4 H36 L40 18" fill="#d98a44" stroke="var(--shadow)" strokeWidth="2.5" strokeLinejoin="round" />
        : <path d="M4 18 Q22 2 40 18 Z" fill="#d98a44" stroke="var(--shadow)" strokeWidth="2.5" strokeLinejoin="round" />}
      {open && <path d="M10 16 L22 8 L34 16" fill="var(--gold)" />}
      <rect x="19" y="20" width="6" height="8" rx="1" fill="var(--gold)" stroke="var(--shadow)" strokeWidth="1.5" />
    </svg>
  )
}
