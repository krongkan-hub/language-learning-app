import { useEffect, useRef, useState } from 'react'

export interface Bar {
  label: string // x-axis label
  value: number
  detail: string // tooltip text
}

interface Props {
  bars: Bar[]
  title: string // names the single series, so no legend box is needed
}

const H = 200
const PAD = { top: 12, right: 8, bottom: 26, left: 28 }
const GAP = 2 // surface gap between adjacent bars

/** Vertical bars over time, one series, with a per-bar hover tooltip and a
 *  table view underneath for anyone who cannot or would rather not read it. */
export function BarChart({ bars, title }: Props) {
  const [hover, setHover] = useState<number | null>(null)
  // Drawn at the container's real width, not scaled: a scaled viewBox shrank
  // the axis text to ~5px on a phone.
  const box = useRef<HTMLDivElement>(null)
  const [W, setW] = useState(640)
  useEffect(() => {
    const el = box.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setW(Math.max(280, Math.round(e.contentRect.width))))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  // An even top, so the three gridlines are evenly spaced (0, 2, 3 was not).
  const peak = Math.max(1, ...bars.map((b) => b.value))
  const max = peak <= 1 ? 1 : Math.ceil(peak / 2) * 2
  const innerW = W - PAD.left - PAD.right
  const innerH = H - PAD.top - PAD.bottom
  const slot = innerW / Math.max(1, bars.length)
  const barW = Math.max(2, Math.min(28, slot - GAP))
  const y = (v: number) => PAD.top + innerH - (v / max) * innerH
  const ticks = [0, max / 2, max].filter((v, i, a) => Number.isInteger(v) && a.indexOf(v) === i)
  // Kept inside the plot so a tooltip at the first or last bar is not cut off.
  const tipLeft = hover === null ? 0 : Math.min(W - 70, Math.max(70, PAD.left + slot * hover + slot / 2))

  return (
    <div className="chart" ref={box}>
      {/* The tooltip is positioned against this box, the plot alone: against
          .chart it also counted the table below and landed hundreds of px low. */}
      <div style={{ position: 'relative', width: W }}>
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} role="img" aria-label={title}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} stroke="var(--line)" strokeWidth={1} />
            <text x={PAD.left - 6} y={y(t) + 4} fontSize={11} textAnchor="end" fill="var(--dim)">{t}</text>
          </g>
        ))}
        {bars.map((b, i) => {
          const cx = PAD.left + slot * i + slot / 2
          const h = y(0) - y(b.value)
          return (
            <g key={b.label} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
               onClick={() => setHover(hover === i ? null : i)}>
              {/* hit target: the whole column, wider and taller than the mark */}
              <rect x={cx - slot / 2} y={PAD.top} width={slot} height={innerH} fill="transparent" />
              {b.value > 0 && (
                <path
                  d={roundedTop(cx - barW / 2, y(b.value), barW, h, Math.min(4, h))}
                  fill="var(--series-1)"
                  opacity={hover === null || hover === i ? 1 : 0.55}
                />
              )}
              {i % Math.ceil(bars.length / Math.max(2, Math.floor(W / 90))) === 0 && (
                <text x={cx} y={H - 8} fontSize={11} textAnchor="middle" fill="var(--dim)">{b.label}</text>
              )}
            </g>
          )
        })}
      </svg>
      {hover !== null && (
        <div
          className="tooltip"
          style={{ left: tipLeft, top: y(bars[hover].value) }}
        >
          {bars[hover].detail}
        </div>
      )}
      </div>
      <details>
        <summary>Show as table</summary>
        <table>
          <tbody>
            {bars.map((b) => (
              <tr key={b.label}><td>{b.detail}</td></tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
}

/** A bar anchored to the baseline with only its data end rounded. */
function roundedTop(x: number, top: number, w: number, h: number, r: number): string {
  return `M${x},${top + h} V${top + r} Q${x},${top} ${x + r},${top} H${x + w - r} Q${x + w},${top} ${x + w},${top + r} V${top + h} Z`
}
