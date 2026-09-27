import { useLayoutEffect, useRef } from 'react'
import type { LogItem } from '../session'

interface Props {
  log: LogItem[]
  drillOpen: boolean
}

/**
 * The conversation. role="log" is a transcript that only ever grows, but it
 * carries no aria-live: the NPC's reply streams in as partial-sentence
 * appends, which a live region would read over and over. The finished turn is
 * announced once through #srAnnounce instead (see Practice).
 */
export function Transcript({ log, drillOpen }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  // The drill sits in normal flow, so opening it shrinks this box — and a
  // scroll container that shrinks keeps its scrollTop, leaving the newest
  // lines below the fold. Every change to the log, and both drill
  // transitions, pin the scroll to the bottom.
  useLayoutEffect(() => {
    const el = ref.current
    if (el) el.scrollTop = el.scrollHeight
  }, [log, drillOpen])

  return (
    <div id="log" role="log" ref={ref}>
      {log.map((item) => <Entry key={item.id} item={item} />)}
    </div>
  )
}

function Entry({ item }: { item: LogItem }) {
  switch (item.kind) {
    case 'turn':
      return (
        <div className={`turn ${item.cls}`}>
          <div className="who">{item.who}</div>
          <div style={item.cls === 'note' ? { whiteSpace: 'pre-line' } : undefined}>{item.text}</div>
        </div>
      )
    case 'vocab':
      return (
        <div className="card">
          <b>📖 {item.word}</b><br /><span>{item.explanation}</span>
        </div>
      )
    case 'error':
      return (
        <div className="turn errorTurn">
          <div className="t">{item.title}</div>
          <div>{item.message}</div>
          <div className="why">{item.detail}</div>
        </div>
      )
  }
}
