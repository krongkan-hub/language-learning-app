import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { fetchScenarios, fetchStats, fetchToday, type Today } from '../api'
import { Hanamaru } from '../../art/Hanamaru'
import { copyFor } from '../copy'
import type { Language, Mode, ScenarioCard, Stats, StatRow, Strings } from '../types'

interface Props {
  lang: Language
  str: Strings
  loadStrings: (lang: Language) => Promise<Strings>
  onStart: (lang: Language, mode: Mode, scenario?: string) => void
}

/**
 * Today's page (#50c): the notebook opens on what to do next. When the coach
 * has corrected this learner, "Up next" is the redo of exactly those red
 * marks (app/review.py builds the session from the same list); otherwise a
 * conversation. Today's 花丸 waits for one finished page — a gentle streak,
 * no nagging. The language is a switch on the cover; everything on the page
 * speaks the language being practised.
 */
export function Setup({ lang, str, loadStrings, onStart }: Props) {
  const [panel, setPanel] = useState<'none' | 'browse' | 'stats'>('none')
  const [pageLang, setPageLang] = useState<Language>(lang)
  const today = useToday(pageLang)
  const c = copyFor(pageLang)
  const t = c.today
  const redo = today?.review ?? []

  useEffect(() => { loadStrings(pageLang) }, [pageLang, loadStrings])

  const open = (which: 'browse' | 'stats') => setPanel(panel === which ? 'none' : which)
  // Coming back from Page complete, the focused button is gone and focus
  // fell to <body>; the page's heading takes it (review of #50d).
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    if (document.activeElement === document.body || document.activeElement === null) heading.current?.focus()
  }, [])
  const now = new Date()

  return (
    <div id="setup" className="today">
      <aside className="cover">
        <div className="brand">
          <RedPenMark />
          <div><b>Red Pen</b><span>赤ペン · LANGUAGE COACH</span></div>
        </div>
        <nav aria-label="Red Pen">
          <button className={panel === 'none' ? 'on' : ''} aria-current={panel === 'none' ? 'page' : undefined}
                  onClick={() => setPanel('none')}>{t.nav.today}</button>
          <button className={panel === 'browse' ? 'on' : ''} aria-current={panel === 'browse' ? 'page' : undefined}
                  id="browseBtn" onClick={() => open('browse')}>{str.web_browse || t.nav.browse}</button>
          <button className={panel === 'stats' ? 'on' : ''} aria-current={panel === 'stats' ? 'page' : undefined}
                  id="progressBtn" onClick={() => open('stats')}>{str.web_progress || t.nav.progress}</button>
          <a id="dashboardLink" href={`/dashboard?language=${pageLang}`}>{str.web_dashboard || t.nav.dashboard}</a>
        </nav>
        <div className="langSwitch" role="group" aria-label="Language">
          {(['English', 'Japanese'] as Language[]).map((l) => (
            <button key={l} aria-pressed={pageLang === l} onClick={() => { setPageLang(l); setPanel('none') }}>
              {l === 'English' ? 'English' : '日本語'}</button>
          ))}
        </div>
      </aside>

      <main className="paper" lang={c.htmlLang}>
        <div className="todayHead">
          <div>
            <div className="pen">{t.date(now)}</div>
            <h1 tabIndex={-1} ref={heading}>{t.greeting(now.getHours())}</h1>
          </div>
          <div className="goal" id="goal">
            <Hanamaru size={44} className={today && today.done_today > 0 ? 'earned' : 'waiting'} />
            <div>
              <b>{today && today.done_today > 0 ? t.goalDone : t.goalWaiting}</b>
              <span>{today && today.streak > 0 ? t.streak(today.streak) : t.goalHint}</span>
            </div>
          </div>
        </div>

        {panel === 'none' && (
          <>
            <section className="upNext" aria-labelledby="upNextTitle">
              {redo.length > 0 ? (
                <>
                  <div className="kicker">{str.web_review_mistakes || t.upNext}</div>
                  <h2 id="upNextTitle">{t.redoTitle(redo.length)}</h2>
                  <ul className="redoList">
                    {redo.slice(0, 3).map((r, i) => (
                      <li key={i}><span className="redmark">{r.was}</span> <span className="pen">{r.fix}</span></li>
                    ))}
                  </ul>
                  <p>{t.redoNote}</p>
                  <button className="primary" onClick={() => onStart(pageLang, 'review')}>{t.redoStart}</button>
                </>
              ) : (
                <>
                  <div className="kicker">{t.freshKicker}</div>
                  <h2 id="upNextTitle">{t.freshTitle}</h2>
                  <p>{t.freshNote}</p>
                  <button className="primary" onClick={() => onStart(pageLang, 'scenario')}>{t.freshStart}</button>
                </>
              )}
            </section>

            <h3 className="fresh">{t.orFresh}</h3>
            <div className="indexCards">
              <IndexCard title={t.conversation[0]} note={t.conversation[1]} onClick={() => onStart(pageLang, 'scenario')} />
              <IndexCard title={t.explain[0]} note={t.explain[1]} onClick={() => onStart(pageLang, 'explain')} />
              <IndexCard title={t.browse[0]} note={t.browse[1]} onClick={() => open('browse')} />
            </div>

            {(today?.recent.length ?? 0) > 0 && (
              <section className="recent" aria-labelledby="recentTitle">
                <h3 id="recentTitle">{t.recent}</h3>
                <ul>
                  {today!.recent.map((r, i) => (
                    <li key={i}><span className="was">{r.was}</span><span className="arrow" aria-hidden="true">→</span>
                      <span className="now">{r.fix}</span></li>
                  ))}
                </ul>
              </section>
            )}
          </>
        )}

        {panel === 'browse' && (
          <ScenarioBrowser lang={pageLang} str={str} onPick={(name) => onStart(pageLang, 'scenario', name)}
                           onClose={() => setPanel('none')} />
        )}
        <div id="statsBox">
          {panel === 'stats' && <StatsPanel lang={pageLang} str={str} onClose={() => setPanel('none')} />}
        </div>
      </main>
    </div>
  )
}

function useToday(lang: Language): Today | null {
  const [data, setData] = useState<Today | null>(null)
  useEffect(() => {
    let live = true
    setData(null)
    fetchToday(lang).then((d) => { if (live) setData(d) })
      .catch(() => { if (live) setData({ review: [], recent: [], done_today: 0, streak: 0 }) })
    return () => { live = false }
  }, [lang])
  return data
}

function IndexCard({ title, note, onClick }: { title: string; note: string; onClick: () => void }) {
  return (
    <button className="indexCard" onClick={onClick}>
      <span className="tape" aria-hidden="true" />
      <b>{title}</b>
      <span>{note}</span>
    </button>
  )
}

function RedPenMark() {
  return (
    <svg width="34" height="34" viewBox="0 0 46 46" aria-hidden="true">
      <rect x="19" y="3" width="9" height="30" rx="2" fill="var(--pen)" transform="rotate(35 23 23)" />
      <path d="M8 38l4-9 5 4z" fill="var(--on-cover)" />
      <path d="M6 42c8-2 14 1 22-1" stroke="var(--pen)" strokeWidth="2.5" fill="none" strokeLinecap="round" />
    </svg>
  )
}

/**
 * 80 cards in one endless column is worse than the random draw it exists to
 * escape, so the browser has a filter and a way back.
 */
function ScenarioBrowser({ lang, str, onPick, onClose }:
    { lang: Language; str: Strings; onPick: (name: string) => void; onClose: () => void }) {
  const [cards, setCards] = useState<ScenarioCard[] | null>(null)
  const [q, setQ] = useState('')
  const search = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetchScenarios(lang).then(setCards).catch(() => setCards([]))
    search.current?.focus()
  }, [lang])

  const needle = q.trim().toLowerCase()
  const shown = (cards || []).filter((sc) => !needle || `${sc.display_name} ${sc.place}`.toLowerCase().includes(needle))

  return (
    <>
      <div id="scenTools" className="on">
        <label htmlFor="scenSearch" id="scenSearchLabel" className="sr-only">{str.web_search || 'Search scenarios…'}</label>
        <input type="text" id="scenSearch" autoComplete="off" ref={search} value={q}
               placeholder={str.web_search || 'Search scenarios…'} onChange={(e) => setQ(e.target.value)}
               style={{ borderColor: cards && !shown.length ? 'var(--bad)' : undefined }} />
        <button className="ghost" onClick={onClose}>{str.web_close || 'Close'}</button>
      </div>
      <div id="scenList">
        {cards === null
          ? <><div className="skel" /><div className="skel" /><div className="skel" /></>
          : shown.map((sc) => <ScenarioItem key={sc.name} sc={sc} onPick={onPick} />)}
      </div>
    </>
  )
}

/**
 * Styled as a card, behaving as a button: role, a tab stop, Enter/Space. The
 * aria-label is built here because the three child texts sit flush against
 * each other, and read as one run-on word from the text content alone.
 */
function ScenarioItem({ sc, onPick }: { sc: ScenarioCard; onPick: (name: string) => void }) {
  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onPick(sc.name) }
  }
  return (
    <div className="scen" role="button" tabIndex={0} onClick={() => onPick(sc.name)} onKeyDown={onKeyDown}
         aria-label={`${sc.display_name}, ${sc.place}, ${sc.mastery_label}, ${sc.plays}×`}>
      <span className="m">{sc.mastery_label} · {sc.plays}×</span>
      <b>{sc.display_name}</b><br /><span className="muted">{sc.place}</span>
    </div>
  )
}

/**
 * Headline numbers as a KPI row, per-scenario history as a table — 80 classes
 * is far past where colour could carry identity. A scenario and an explain
 * topic share columns but not meaning, so each gets its own headed table.
 */
function StatsPanel({ lang, str, onClose }: { lang: Language; str: Strings; onClose: () => void }) {
  const [s, setS] = useState<Stats | null>(null)
  useEffect(() => { fetchStats(lang).then(setS).catch(() => setS({})) }, [lang])
  if (!s) return <div className="skel" />

  const c = copyFor(lang)
  const o = s.overall || {}
  const words = (s.vocab?.learned_words || 0) + (s.vocab?.due_words || 0)
  const rate = o.overall_completion_rate ?? 0
  const played = (rows?: Record<string, StatRow>) =>
    Object.values(rows || {}).filter((x) => (x.plays || 0) > 0).sort((a, b) => (b.plays || 0) - (a.plays || 0))
  const scen = played(s.scenarios), topics = played(s.topics), mistakes = s.mistakes || []

  return (
    <>
      <div className="kpis">
        <Kpi n={o.sessions_played ?? 0} label={c.kpi.sessions} />
        <Kpi n={`${o.tasks_completed ?? 0}/${o.tasks_attempted ?? 0}`} label={c.kpi.tasks} meter={rate} />
        <Kpi n={`${rate}%`} label={c.kpi.completion} />
        <Kpi n={words} label={c.kpi.words} />
      </div>
      {mistakes.length > 0 && (
        <>
          <h3 className="statHead">{str.stats_mistakes_header || 'Mistakes you keep making:'}{' '}
            <span className="statCount">{mistakes.length}</span></h3>
          <ul className="mistakeList">
            {mistakes.map((m, i) => (
              <li key={i}><span className="was">{m.example_quoted}</span>
                <span className="now">{m.example_correction}</span><span className="n">×{m.occurrences}</span></li>
            ))}
          </ul>
        </>
      )}
      <StatTable rows={scen} heading={str.web_stat_scenarios || 'Scenarios'} str={str} />
      <StatTable rows={topics} heading={str.web_stat_topics || 'Explain topics'} str={str} />
      {!mistakes.length && !scen.length && !topics.length && (
        <p className="muted">{str.web_no_stats || 'No sessions recorded yet.'}</p>
      )}
      <p style={{ marginTop: 14 }}><button className="ghost" onClick={onClose}>{str.web_close || 'Close'}</button></p>
    </>
  )
}

function Kpi({ n, label, meter }: { n: string | number; label: string; meter?: number }) {
  return (
    <div className="kpi">
      <div className="n">{n}</div>
      <div className="l">{label}</div>
      {meter !== undefined && <div className="meter"><i style={{ width: `${Math.max(0, Math.min(100, meter))}%` }} /></div>}
    </div>
  )
}

function StatTable({ rows, heading, str }: { rows: StatRow[]; heading: string; str: Strings }) {
  if (!rows.length) return null
  const right = { textAlign: 'right' as const }
  return (
    <>
      <h3 className="statHead">{heading} <span className="statCount">{rows.length}</span></h3>
      <table className="scen">
        <thead><tr><th />
          <th style={right}>{str.web_col_plays || 'Plays'}</th>
          <th style={right}>{str.web_col_best || 'Best'}</th>
          <th style={right}>{str.web_col_mastery || 'Mastery'}</th></tr></thead>
        <tbody>
          {rows.map((x, i) => (
            <tr key={i}>
              <td className="name">{x.scenario_name || x.topic_name || ''}</td>
              <td className="num">{x.plays || 0}</td>
              <td className="num">{x.best_pct || 0}%</td>
              {/* the mastery ladder labels are localized in STR */}
              <td className="mastery">{(x.mastery && str[x.mastery]) || x.mastery || ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
