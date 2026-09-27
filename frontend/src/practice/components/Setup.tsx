import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { fetchScenarios, fetchStats } from '../api'
import { copyFor } from '../copy'
import type { Language, Mode, ScenarioCard, Stats, StatRow, Strings } from '../types'

interface Props {
  lang: Language
  str: Strings
  loadStrings: (lang: Language) => Promise<Strings>
  onStart: (lang: Language, mode: Mode, scenario?: string) => void
}

/**
 * The landing page. Each language card says what that language has cost you
 * in progress terms — the one thing a learner wants to know before choosing.
 * The cards and the explain row are bilingual on purpose: no language has
 * been chosen yet, so each card speaks its own.
 */
export function Setup({ lang, str, loadStrings, onStart }: Props) {
  const [panel, setPanel] = useState<'none' | 'browse' | 'stats'>('none')
  const [browseLang, setBrowseLang] = useState(lang)
  const subs = useLandingSubtitles()

  const open = async (which: 'browse' | 'stats') => {
    await loadStrings(lang)
    setBrowseLang(lang)
    setPanel(which)
  }

  return (
    <div id="setup"><div id="setupInner">
      <h1>Language Coach</h1>
      <p className="lede">Practise a real conversation. A scenario is picked for you,
        and the coach corrects you as you go.</p>

      <div className="langs">
        <button className="lang" onClick={() => onStart('English', 'scenario')}>
          <b>English</b><span id="enSub">{subs.English || 'Start a conversation'}</span></button>
        <button className="lang" onClick={() => onStart('Japanese', 'scenario')}>
          <b>日本語</b><span id="jaSub">{subs.Japanese || '会話をはじめる'}</span></button>
      </div>

      <p className="lede" id="explainLede" style={{ margin: '22px 0 10px' }}>Or explain something,
        and answer when they don't follow.</p>
      <div className="langs">
        <button className="lang" onClick={() => onStart('English', 'explain')}>
          <b id="explainEn">Explain · English</b><span id="explainEnSub">Say more than one sentence</span></button>
        <button className="lang" onClick={() => onStart('Japanese', 'explain')}>
          <b id="explainJa">説明する · 日本語</b><span id="explainJaSub">一文より長く話す</span></button>
      </div>

      <div className="row">
        <button className="ghost" id="progressBtn" onClick={() => open('stats')}>{str.web_progress || 'Progress'}</button>
        <button className="ghost" id="browseBtn" onClick={() => open('browse')}>{str.web_browse || 'Browse all 80 scenarios'}</button>
        <a className="ghost" id="dashboardLink" href={`/dashboard?language=${lang}`} style={{ textDecoration: 'none' }}>{str.web_dashboard || 'Dashboard'}</a>
      </div>

      {panel === 'browse' && (
        <ScenarioBrowser lang={browseLang} str={str} onPick={(name) => onStart(browseLang, 'scenario', name)}
                         onClose={() => setPanel('none')} />
      )}
      <div id="statsBox">
        {panel === 'stats' && <StatsPanel lang={browseLang} str={str} onClose={() => setPanel('none')} />}
      </div>
    </div></div>
  )
}

function useLandingSubtitles(): Partial<Record<Language, string>> {
  const [subs, setSubs] = useState<Partial<Record<Language, string>>>({})
  useEffect(() => {
    for (const l of ['English', 'Japanese'] as Language[]) {
      fetchStats(l).then((s) => {
        const played = s.overall?.sessions_played || 0
        if (!played) return
        // Words COLLECTED, not "learned": learned_words counts only those
        // used correctly three times, and greeted a learner with 43 sessions
        // behind them by saying 0.
        const words = (s.vocab?.learned_words || 0) + (s.vocab?.due_words || 0)
        setSubs((prev) => ({ ...prev, [l]: copyFor(l).landing(played, s.overall?.tasks_completed || 0, words) }))
      }).catch(() => { /* keep the default subtitle */ })
    }
  }, [])
  return subs
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
        <label htmlFor="scenSearch" id="scenSearchLabel" className="sr-only">{str.web_search || 'Search scenarios'}</label>
        <input type="text" id="scenSearch" autoComplete="off" ref={search} value={q}
               placeholder={str.web_search} onChange={(e) => setQ(e.target.value)}
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
