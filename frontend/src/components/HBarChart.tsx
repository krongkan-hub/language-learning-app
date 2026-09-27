export interface HBar {
  name: string
  value: number | null // 0-100
  title: string // hover text
}

/** Horizontal bars for a ranked list, each directly labelled with its value,
 *  so the numbers never depend on reading a colour or an axis. */
export function HBarChart({ rows, empty }: { rows: HBar[]; empty: string }) {
  if (!rows.length) return <p className="muted">{empty}</p>
  return (
    <div role="list">
      {rows.map((r) => (
        <div className="hbar" role="listitem" key={r.name} title={r.title}>
          <span className="name">{r.name}</span>
          <span className="track">
            <span className="fill" style={{ display: 'block', width: `${r.value ?? 0}%` }} />
          </span>
          <span className="val">{r.value === null ? '—' : `${r.value}%`}</span>
        </div>
      ))}
    </div>
  )
}
