interface Props {
  value: string | number
  label: string
  sub?: string
}

/** One headline number. A single figure needs no chart. */
export function StatTile({ value, label, sub }: Props) {
  return (
    <div className="panel tile">
      <div className="n">{value}</div>
      <div className="l">{label}</div>
      {sub && <div className="s">{sub}</div>}
    </div>
  )
}
