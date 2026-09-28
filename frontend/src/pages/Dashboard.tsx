import { useEffect, useState } from 'react'
import '../theme.css'
import { fetchDashboard } from '../api'
import type { Dashboard as Data, Language } from '../types'
import { BarChart } from '../components/BarChart'
import { HBarChart } from '../components/HBarChart'
import { StatTile } from '../components/StatTile'

const LABELS = {
  English: {
    title: 'Your progress', back: '← Back to practice', sessions: 'Sessions', days: 'active days',
    completion: 'Task completion', streak: 'Day streak', words: 'Words learned', due: 'still practising',
    repeats: 'Repeated mistakes', repeatsSub: 'types of mistake made more than once', weekly: 'Sessions per week',
    hardest: 'Hardest scenarios (completion rate)', mistakes: 'Mistakes you keep making', practising: 'Words you are practising',
    none: 'Nothing here yet — try a scenario first.', loading: 'Loading…', error: 'Could not load the dashboard.',
    week: 'week of', uses: 'uses', sessionsUnit: 'sessions', tasksUnit: 'tasks done', noRepeats: 'None yet — no mistake has come up twice.',
    perf: 'Response time (last 7 days)', stage: 'Step', count: 'Runs', p50: 'Typical', p95: 'Slowest 5%',
    noPerf: 'No timings yet — they are recorded while the server runs.',
    table: 'Show as table', colScenario: 'Scenario', colDone: 'Tasks done', colPlays: 'Plays', colTries: 'Avg. tries',
    colMistake: 'You wrote → correct', colTimes: 'Times', colWord: 'Word', colUses: 'Used',
  },
  Japanese: {
    title: '学習の記録', back: '← 練習に戻る', sessions: 'セッション', days: '日間 学習',
    completion: 'タスク達成率', streak: '連続日数', words: '覚えた単語', due: '語を練習中',
    repeats: '繰り返している間違い', repeatsSub: '2回以上した間違いの種類', weekly: '週ごとのセッション',
    hardest: '難しいシナリオ（達成率）', mistakes: '繰り返している間違い', practising: '練習中の単語',
    none: 'まだ記録がありません。まずシナリオを始めましょう。', loading: '読み込み中…', error: '読み込めませんでした。',
    week: '週の開始日', uses: '回使用', sessionsUnit: 'セッション', tasksUnit: 'タスク達成', noRepeats: 'まだありません。2回以上した間違いはありません。',
    perf: '応答時間（過去7日）', stage: '処理', count: '回数', p50: '中央値', p95: '遅い方から5%',
    noPerf: 'まだ記録がありません。',
    table: '表で見る', colScenario: 'シナリオ', colDone: '達成', colPlays: 'プレイ回数', colTries: '平均挑戦回数',
    colMistake: '書いた文 → 正しい形', colTimes: '回数', colWord: '単語', colUses: '使用',
  },
} as const

// The practice screen links here with ?language=, so a Japanese learner does
// not land on the English learner's (possibly empty) record.
function initialLanguage(): Language {
  return new URLSearchParams(window.location.search).get('language') === 'Japanese' ? 'Japanese' : 'English'
}

export function Dashboard() {
  const [language, setLanguage] = useState<Language>(initialLanguage)
  const [data, setData] = useState<Data | null>(null)
  const [failed, setFailed] = useState(false)
  const L = LABELS[language]

  useEffect(() => {
    let live = true
    setData(null)
    setFailed(false)
    fetchDashboard(language)
      .then((d) => live && setData(d))
      .catch(() => live && setFailed(true))
    const url = new URL(window.location.href)
    url.searchParams.set('language', language)
    window.history.replaceState(null, '', url)
    // a screen reader picks its voice from lang; the tab says which page this is
    document.documentElement.lang = language === 'Japanese' ? 'ja' : 'en'
    document.title = `${LABELS[language].title} — Language Coach`
    return () => { live = false }
  }, [language])

  return (
    <main className="page">
      <div className="header">
        <h1>{L.title}</h1>
        <div className="toggle" role="group" aria-label="Language">
          {(['English', 'Japanese'] as const).map((l) => (
            <button key={l} aria-pressed={language === l} lang={l === 'Japanese' ? 'ja' : 'en'} onClick={() => setLanguage(l)}>
              {l === 'English' ? 'English' : '日本語'}
            </button>
          ))}
        </div>
        <a className="back" href={`/?language=${language}`}>{L.back}</a>
      </div>

      {failed && <p className="muted" role="alert">{L.error}</p>}
      {!data && !failed && <p className="muted" role="status">{L.loading}</p>}
      {data && <Body data={data} L={L} />}
    </main>
  )
}

function Body({ data, L }: { data: Data; L: (typeof LABELS)[Language] }) {
  const s = data.summary
  if (!s.sessions) return <p className="muted">{L.none}</p>
  return (
    <>
      <div className="grid tiles">
        <StatTile value={s.sessions} label={L.sessions} sub={`${s.active_days} ${L.days}`} />
        <StatTile value={`${s.completion_rate}%`} label={L.completion} sub={`${s.completed} / ${s.attempted}`} />
        <StatTile value={s.streak_days} label={L.streak} />
        <StatTile value={s.learned} label={L.words} sub={`${s.due} ${L.due}`} />
        <StatTile value={s.repeated_classes} label={L.repeats} sub={L.repeatsSub} />
      </div>

      <section className="panel">
        <h2>{L.weekly}</h2>
        <BarChart
          title={L.weekly}
          tableLabel={L.table}
          bars={data.weekly.map((w) => ({
            label: w.week.slice(5),
            value: w.sessions,
            detail: `${L.week} ${w.week}: ${w.sessions} ${L.sessionsUnit} · ${w.completed}/${w.attempted} ${L.tasksUnit}`,
          }))}
        />
      </section>

      <div className="grid two">
        <section className="panel">
          <h2>{L.hardest}</h2>
          <HBarChart
            empty={L.none}
            tableLabel={L.table}
            columns={[L.colScenario, L.colDone, L.colPlays, L.colTries]}
            rows={data.scenarios.filter((r) => r.attempted > 0).slice(0, 8).map((r) => ({
              name: r.scenario_name,
              value: r.completion_rate,
              cells: [`${r.completed}/${r.attempted}`, r.plays, r.avg_attempts ?? '—'],
            }))}
          />
        </section>

        <section className="panel">
          <h2>{L.mistakes}</h2>
          {data.mistakes.length === 0 ? (
            <p className="muted">{L.noRepeats}</p>
          ) : (
            <table>
              <thead><tr><th scope="col">{L.colMistake}</th><th scope="col" className="num">{L.colTimes}</th></tr></thead>
              <tbody>
                {data.mistakes.map((m) => (
                  <tr key={m.normalized_key}>
                    <td><span className="was">{m.example_quoted}</span> → <span className="now">{m.example_correction}</span></td>
                    <td className="num">×{m.occurrences}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>

      <section className="panel" style={{ marginTop: 14 }}>
        <h2>{L.practising}</h2>
        {data.words.length === 0 ? (
          <p className="muted">{L.none}</p>
        ) : (
          <table>
            <thead><tr><th scope="col">{L.colWord}</th><th scope="col" className="num">{L.colUses}</th></tr></thead>
            <tbody>
              {data.words.map((w) => (
                <tr key={w.word}>
                  <td><strong>{w.word}</strong><div className="muted">{w.explanation}</div></td>
                  <td className="num">{w.times_correct}/3 {L.uses}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="panel" style={{ marginTop: 14 }}>
        <h2>{L.perf}</h2>
        {data.performance.length === 0 ? (
          <p className="muted">{L.noPerf}</p>
        ) : (
          <table>
            <thead>
              <tr><th>{L.stage}</th><th className="num">{L.count}</th><th className="num">{L.p50}</th><th className="num">{L.p95}</th></tr>
            </thead>
            <tbody>
              {data.performance.map((p) => (
                <tr key={p.name}>
                  <td>{p.name}</td>
                  <td className="num">{p.count}</td>
                  <td className="num">{seconds(p.p50_ms)}</td>
                  <td className="num">{seconds(p.p95_ms)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  )
}

function seconds(ms: number): string {
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`
}
