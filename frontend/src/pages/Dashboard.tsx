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
    completion: 'Tasks done', streak: 'Day streak', words: 'Words learned', due: 'still practising',
    repeats: 'Repeated mistakes', repeatsSub: 'kinds made more than once', weekly: 'Sessions per week',
    hardest: 'Hardest scenarios (tasks done)', mistakes: 'Mistakes you keep making', practising: 'Words you are practising',
    none: 'Nothing here yet — play a scenario first.', loading: 'Loading…', error: 'Could not load the dashboard.',
    week: 'week of', uses: 'uses', noRepeats: 'None yet — no mistake has come up twice.',
    perf: 'Response time (last 7 days)', stage: 'Step', count: 'Runs', p50: 'Typical', p95: 'Slowest 5%',
    noPerf: 'No timings yet — they are recorded while the server runs.',
  },
  Japanese: {
    title: '学習の記録', back: '← 練習に戻る', sessions: 'セッション', days: '日',
    completion: 'タスク達成率', streak: '連続日数', words: '覚えた単語', due: '練習中',
    repeats: '繰り返しの間違い', repeatsSub: '2回以上の間違いの種類', weekly: '週ごとのセッション',
    hardest: '難しいシナリオ（達成率）', mistakes: '繰り返している間違い', practising: '練習中の単語',
    none: 'まだ記録がありません。まずシナリオを始めましょう。', loading: '読み込み中…', error: '読み込めませんでした。',
    week: '週', uses: '回使用', noRepeats: 'まだありません。',
    perf: '応答時間（過去7日）', stage: '段階', count: '回数', p50: '通常', p95: '遅い5%',
    noPerf: 'まだ記録がありません。',
  },
} as const

export function Dashboard() {
  const [language, setLanguage] = useState<Language>('English')
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
    return () => { live = false }
  }, [language])

  return (
    <main className="page">
      <div className="header">
        <h1>{L.title}</h1>
        <div className="toggle" role="group" aria-label="Language">
          {(['English', 'Japanese'] as const).map((l) => (
            <button key={l} aria-pressed={language === l} onClick={() => setLanguage(l)}>
              {l === 'English' ? 'English' : '日本語'}
            </button>
          ))}
        </div>
        <a href="/">{L.back}</a>
      </div>

      {failed && <p className="muted">{L.error}</p>}
      {!data && !failed && <p className="muted">{L.loading}</p>}
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
          bars={data.weekly.map((w) => ({
            label: w.week.slice(5),
            value: w.sessions,
            detail: `${L.week} ${w.week}: ${w.sessions} · ${w.completed}/${w.attempted}`,
          }))}
        />
      </section>

      <div className="grid two">
        <section className="panel">
          <h2>{L.hardest}</h2>
          <HBarChart
            empty={L.none}
            rows={data.scenarios.filter((r) => r.attempted > 0).slice(0, 8).map((r) => ({
              name: r.scenario_name,
              value: r.completion_rate,
              title: `${r.completed}/${r.attempted} · ${r.plays}× · ${r.avg_attempts ?? '—'}`,
            }))}
          />
        </section>

        <section className="panel">
          <h2>{L.mistakes}</h2>
          {data.mistakes.length === 0 ? (
            <p className="muted">{L.noRepeats}</p>
          ) : (
            <table>
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
