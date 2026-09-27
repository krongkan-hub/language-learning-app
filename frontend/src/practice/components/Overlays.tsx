// The full-screen layers over the conversation: the loading screen, the
// end-of-session summary, and the transient notices (banner, toasts).
import { useEffect, type Dispatch } from 'react'
import { copyFor } from '../copy'
import { scoreClass, whatsNext, type Action, type SessionState } from '../session'

const BOOT_ORDER = ['preparing', 'greeting', 'ready']

/**
 * role="status": the copy changes twice (preparing -> greeting), and a screen
 * reader user looking at an otherwise silent full-screen overlay needs to hear it.
 */
export function Boot({ state }: { state: SessionState }) {
  const stage = state.boot
  const [what, sub] = stage ? copyFor(state.lang).boot[stage] : ['', '']
  return (
    <div id="boot" role="status" className={stage ? 'on' : ''}>
      <div className="ring" />
      <div id="bootWhat">{what}</div>
      <div id="bootSub">{sub}</div>
      <div id="bootSteps">
        {BOOT_ORDER.map((s, i) => <b key={s} className={stage && i <= BOOT_ORDER.indexOf(stage) ? 'on' : ''} />)}
      </div>
    </div>
  )
}

interface DoneProps {
  state: SessionState
  onAgain: () => void
  onReview: () => void
}

/**
 * The summary offers the two things a learner who just finished wants: look
 * back at what they were corrected on, or go straight into another session
 * — not a reload that throws away the conversation and the language choice.
 */
export function Done({ state, onAgain, onReview }: DoneProps) {
  const sum = state.summary
  if (!sum) return <div id="done" />
  const c = copyFor(state.lang)
  return (
    <div id="done" className="on">
      <div id="doneCard">
        <div id="doneScore" className={scoreClass(sum.done, sum.outOf)}>{sum.done}/{sum.outOf || '?'}</div>
        <p id="doneLine" className="muted">{c.doneLine(sum.done, sum.missed)}</p>
        <div id="doneWords">{state.words.map((w, i) => <span key={i}>{w}</span>)}</div>
        <p id="doneNext" className="muted">{whatsNext(state.lang, sum.progress, sum.wordsDue)}</p>
        <p style={{ marginTop: 20, display: 'flex', gap: 10, justifyContent: 'center' }}>
          <button id="againBtn" onClick={onAgain}>{state.str.web_again || 'Practise again'}</button>
          <button className="ghost" id="reviewBtn" onClick={onReview}>{state.str.web_review || 'Review conversation'}</button>
        </p>
      </div>
    </div>
  )
}

export function Notices({ state, dispatch }: { state: SessionState; dispatch: Dispatch<Action> }) {
  const { banner, toasts } = state
  // a passing notice clears itself; a fatal one stays
  useEffect(() => {
    if (!banner || banner.fatal) return
    const t = setTimeout(() => dispatch({ type: 'dismissBanner', id: banner.id }), 4000)
    return () => clearTimeout(t)
  }, [banner, dispatch])
  return (
    <>
      {banner && <div id="banner" className={banner.fatal ? 'fatal' : ''}>{banner.text}</div>}
      {toasts.map((t) => <Toast key={t.id} id={t.id} text={t.text} dispatch={dispatch} />)}
    </>
  )
}

function Toast({ id, text, dispatch }: { id: number; text: string; dispatch: Dispatch<Action> }) {
  useEffect(() => {
    const t = setTimeout(() => dispatch({ type: 'dismissToast', id }), 2700)
    return () => clearTimeout(t)
  }, [id, dispatch])
  return <div className="toast">{text}</div>
}
