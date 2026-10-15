import { useEffect, useRef, useState, type KeyboardEvent, type RefObject } from 'react'
import { copyFor } from '../copy'
import { isSubmitKey } from '../keys'
import type { Language } from '../types'

interface Props {
  drill: { target: string; remaining: number; msg: string }
  lang: Language
  endRef: RefObject<HTMLButtonElement | null>
  onSubmit: (text: string) => void
}

/**
 * Retype the correction. This is the one place a learner is deliberately held
 * (the server 409s a skip mid-drill by design), so it is a modal dialog to
 * assistive tech too: Tab / Shift+Tab cycle between its two controls only.
 *
 * Escape does NOT close it — there is no cancel to wire up, and adding one
 * would change what the app does rather than how it is exposed. It moves
 * focus to End instead, which ends the session from any state: the one real
 * way out, reached by keyboard.
 */
export function Drill({ drill, lang, endRef, onSubmit }: Props) {
  const c = copyFor(lang)
  const [text, setText] = useState('')
  const input = useRef<HTMLInputElement>(null)
  const ok = useRef<HTMLButtonElement>(null)

  // a new target (the next correction, or a fresh drill) starts empty and focused
  useEffect(() => {
    setText('')
    input.current?.focus()
  }, [drill.target])

  const submit = () => onSubmit(text)

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Tab') {
      const first = input.current, last = ok.current
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus() }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus() }
    } else if (e.key === 'Escape') {
      e.preventDefault()
      endRef.current?.focus()
    }
  }

  return (
    <div id="drill" className="on" role="dialog" aria-modal="true" aria-labelledby="drillLabel" onKeyDown={onKeyDown}>
      <div className="t">
        <span id="drillLabel">{c.rewrite}</span>
        <span id="drillLeft">{drill.remaining > 1 ? c.left(drill.remaining) : ''}</span>
      </div>
      <code id="drillTarget">{drill.target}</code>
      <div className="drillRow">
        <label htmlFor="drillInput" className="sr-only">{c.card.retypeLabel}</label>
        <input type="text" id="drillInput" autoComplete="off" ref={input} value={text}
               onChange={(e) => setText(e.target.value)}
               onKeyDown={(e) => { if (isSubmitKey(e)) submit() }} />
        <button ref={ok} className="fixIt" onClick={submit}>{c.card.fixIt}</button>
      </div>
      <div id="drillMsg" className="muted">{drill.msg}</div>
    </div>
  )
}
