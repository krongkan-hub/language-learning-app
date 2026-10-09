import { useLayoutEffect, useRef, type ReactNode } from 'react'
import { Character } from '../../art/Character'
import { lookFor } from '../../art/characters'
import type { LogItem } from '../session'
import type { Art } from '../types'

interface Props {
  log: LogItem[]
  drillOpen: boolean
  marks?: Record<number, string[]>
  art?: Art | null
}

/**
 * The conversation. role="log" is a transcript that only ever grows, but it
 * carries no aria-live: the NPC's reply streams in as partial-sentence
 * appends, which a live region would read over and over. The finished turn is
 * announced once through #srAnnounce instead (see Practice).
 */
export function Transcript({ log, drillOpen, marks = {}, art = null }: Props) {
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
    <div id="log" className="paper" role="log" ref={ref}>
      {log.map((item) => <Entry key={item.id} item={item} marks={marks[item.id] ?? []} art={art} />)}
    </div>
  )
}

/**
 * The learner's line with the red pen's circles on it: every span the coach
 * corrected this session, found where it was written. The circle is drawn
 * by CSS; the words stay plain text for a screen reader, which hears the
 * correction itself from the coach.
 */
export function circled(text: string, marks: string[]): ReactNode[] {
  const spans = marks.map((m) => m.trim().replace(/[.!?。！？]+$/u, '')).filter((m) => m.length > 1)
    .sort((x, y) => y.length - x.length)          // "I have two dollar" before "I have"
  if (!spans.length) return [text]
  // The coach quotes loosely: case, a curly or straight apostrophe, spacing
  // (app/coach/filters.py normalises the same). Latin words are matched
  // whole, so "is" never circles the "is" in "this"; Japanese has no spaces.
  const flexible = (m: string) => m.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    .replace(/['’‘]/g, "['’‘]").replace(/\s+/g, '\\s+')
  const edge = (m: string) => (/^[\p{Script=Latin}\p{N}]/u.test(m) ? '(?<![\\p{L}\\p{N}])' : '')
  const tail = (m: string) => (/[\p{Script=Latin}\p{N}]$/u.test(m) ? '(?![\\p{L}\\p{N}])' : '')
  const pattern = new RegExp(`(${spans.map((m) => edge(m) + flexible(m) + tail(m)).join('|')})`, 'iu')
  return text.split(pattern).map((part, i) =>
    i % 2 ? <span key={i} className="redmark">{part}</span> : part)
}

function Entry({ item, marks, art }: { item: LogItem; marks: string[]; art: Art | null }) {
  switch (item.kind) {
    case 'turn':
      return (
        <div className={`turn ${item.cls}`}>
          {item.cls === 'npc' && art && (
            <span className="face"><Character look={lookFor(art.speaker)} crop="face" size={34} /></span>
          )}
          <div className="who">{item.who}</div>
          <div style={item.cls === 'note' ? { whiteSpace: 'pre-line' } : undefined}>
            {item.cls === 'you' ? circled(item.text, marks) : item.text}
          </div>
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
