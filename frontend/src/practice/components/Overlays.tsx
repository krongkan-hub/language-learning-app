// The full-screen layers over the conversation: the loading screen, the
// end-of-session summary, and the transient notices (banner, toasts).
import { useEffect, useRef, type Dispatch } from 'react'
import { copyFor } from '../copy'
import { bestLine, scoreClass, whatsNext, type Action, type SessionState } from '../session'
import { Hanamaru } from '../../art/Hanamaru'

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
  onHome: () => void
}

/**
 * Page complete (#50d). Ends on the session's best moment — the peak-end
 * rule: a page with a task done earns the big 花丸, then the fixes (each
 * with its own, since every red mark was retyped right to get here), the
 * learner's best clean line, and the words. One empty page is "closed",
 * not scolded. Focus moves in, or a keyboard user is left behind it.
 */
export function Done({ state, onAgain, onReview, onHome }: DoneProps) {
  const sum = state.reviewing ? null : state.summary
  const again = useRef<HTMLButtonElement>(null)
  useEffect(() => { if (sum) again.current?.focus() }, [sum])
  if (!sum) return <div id="done" />
  const c = copyFor(state.lang)
  const p = c.page
  const earned = sum.done > 0
  const best = bestLine(state)
  return (
    <div id="done" className="on" role="dialog" aria-modal="true" aria-labelledby="doneTitle" aria-describedby="doneLine">
      <div id="doneCard" className="paper">
        <section className="peak">
          <Hanamaru size={150} className={earned ? 'earned' : 'waiting'} />
          <h2 id="doneTitle">{earned ? p.title : p.closed}</h2>
          <div id="doneScore" className={scoreClass(sum.done, sum.outOf)}>{sum.done}/{sum.outOf || '?'}</div>
          <p id="doneLine" className="muted">{c.doneLine(sum.done, sum.missed)}</p>
          {state.hanamaru > 0 && <p className="pen fixedLine">{p.fixedLine(state.hanamaru)}</p>}
          {best && (
            <div className="bestLine">
              <b>{p.best}</b>
              <q>{best}</q>
              <span>{p.bestWhy}</span>
            </div>
          )}
        </section>
        <section className="fixed">
          {state.fixes.length > 0 && (
            <div id="doneFixes">
              <h3>{p.fixedHead} <span className="statCount">{state.fixes.length}</span></h3>
              <ul>
                {state.fixes.map((f) => (
                  <li key={f.was}>
                    <span><span className="was">{f.was}</span><span className="now">{f.now}</span></span>
                    <Hanamaru size={36} />
                  </li>
                ))}
              </ul>
              <p className="muted">{p.comeBack}</p>
            </div>
          )}
          {state.words.length > 0 && (
            <div id="doneWords" aria-label={p.words}>{state.words.map((w, i) => <span key={i}>{w}</span>)}</div>
          )}
          <p id="doneNext" className="muted">{whatsNext(state.lang, sum.progress, sum.wordsDue)}</p>
          <div className="doneButtons">
            <button id="againBtn" className="primary" ref={again} onClick={onAgain}>{state.str.web_again || 'Practice again'}</button>
            <button className="ghost" id="reviewBtn" onClick={onReview}>{state.str.web_review || 'Review conversation'}</button>
            <button className="ghost" id="homeBtn" onClick={onHome}>{p.home}</button>
          </div>
        </section>
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
