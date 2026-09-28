export interface HBar {
  name: string
  value: number | null // 0-100
  cells: (string | number)[] // the row's figures for the table view, one per `columns` entry after the name
}

interface Props {
  rows: HBar[]
  empty: string
  columns: string[] // table headers: the name column first, then one per cell
  tableLabel: string
}

/** Horizontal bars for a ranked list, each directly labelled with its value,
 *  so the numbers never depend on reading a colour or an axis. The details
 *  (tasks done, plays, tries) used to live only in a hover title, which no
 *  keyboard, touch or screen-reader user could reach; they are a table now. */
export function HBarChart({ rows, empty, columns, tableLabel }: Props) {
  if (!rows.length) return <p className="muted">{empty}</p>
  return (
    <>
      <div role="list">
        {rows.map((r) => (
          <div className="hbar" role="listitem" key={r.name}>
            <span className="name">{r.name}</span>
            <span className="track" aria-hidden="true">
              <span className="fill" style={{ display: 'block', width: `${r.value ?? 0}%` }} />
            </span>
            <span className="val">{r.value === null ? '—' : `${r.value}%`}</span>
          </div>
        ))}
      </div>
      <details>
        <summary>{tableLabel}</summary>
        <table>
          <thead>
            <tr>{columns.map((c, i) => <th key={c} scope="col" className={i ? 'num' : undefined}>{c}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.name}><td>{r.name}</td>{r.cells.map((c, i) => <td key={i} className="num">{c}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </details>
    </>
  )
}
