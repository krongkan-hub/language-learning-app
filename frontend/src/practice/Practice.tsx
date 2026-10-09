import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import * as api from './api'
import { copyFor } from './copy'
import { remember, remembered } from './resume'
import { initialState, reduce } from './session'
import { useEventStream } from './useEventStream'
import type { Language, Mode, Strings } from './types'
import { Drill } from './components/Drill'
import { Header } from './components/Header'
import { Boot, Done, Notices } from './components/Overlays'
import { Setup } from './components/Setup'
import { SidePanel } from './components/SidePanel'
import { Stage } from './components/Stage'
import { Hanamaru } from '../art/Hanamaru'
import { Transcript } from './components/Transcript'
import { isSubmitKey } from './keys'
import './practice.css'

/**
 * The practice screen: pick a language, hold a roleplay conversation, get
 * corrected. State lives in one reducer (session.ts); this component turns
 * learner actions into API calls and hands server events to the reducer.
 */
/** The 花丸 count while its pop is on screen, else 0: 1.8s per new one. */
function usePop(count: number): number {
  const [shown, setShown] = useState(0)
  useEffect(() => {
    if (count === 0) { setShown(0); return }
    setShown(count)
    const t = setTimeout(() => setShown(0), 1800)
    return () => clearTimeout(t)
  }, [count])
  return shown
}

export function Practice() {
  const [state, dispatch] = useReducer(reduce, undefined, () => initialState())
  // Kept apart from state.sid: a session resumed at its summary has an id
  // but nothing left to stream.
  const [streamSid, setStreamSid] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const endRef = useRef<HTMLButtonElement>(null)
  const sayRef = useRef<HTMLInputElement>(null)
  const { sid, lang, mode, str } = state
  const pop = usePop(state.hanamaru)

  useEventStream(streamSid, dispatch)
  // one request at a time for Skip and the drill: a double click skipped two tasks
  const inFlight = useRef(false)

  // a screen reader picks its voice from lang: Japanese text read as English is noise
  useEffect(() => {
    document.documentElement.lang = copyFor(lang).htmlLang
  }, [lang])

  // Only the latest language asked for may land: switching EN→JA→EN fast
  // let the Japanese strings arrive last and label an English page (review #57).
  const wanted = useRef<Language | null>(null)
  const loadStrings = useCallback(async (l: Language): Promise<Strings> => {
    wanted.current = l
    const s = await api.fetchStrings(l)
    if (wanted.current === l) dispatch({ type: 'strings', lang: l, str: s })
    return s
  }, [])

  // this session survives a reload; a finished one does not, and has nothing left to stream
  useEffect(() => {
    if (sid) remember(state.summary ? null : sid)
    if (state.summary) setStreamSid(null)
  }, [sid, state.summary])

  useEffect(() => {
    if (state.open) sayRef.current?.focus()
  }, [state.open])

  // pick a session back up after a reload
  useEffect(() => {
    const saved = remembered()
    if (!saved) return
    api.fetchSnapshot(saved).then(async (snap) => {
      if (!snap) { remember(null); return }
      await loadStrings(snap.language)
      dispatch({ type: 'resumed', snap: { ...snap, session: saved } })
      if (snap.state !== 'finished') setStreamSid(saved)
    })
  }, [loadStrings])

  const start = async (l: Language, m: Mode, scenario?: string) => {
    dispatch({ type: 'booting' })
    try {
      await loadStrings(l)
      const header = await api.createSession(l, m, scenario)
      dispatch({ type: 'started', header })
      setStreamSid(header.session)
    } catch (e) {
      dispatch({ type: 'banner', text: String((e as Error).message || e), fatal: true })
    }
  }

  // The coach takes ~10s after the NPC has already replied (p50, from the
  // spans), and the box used to stay disabled through all of it. Typing is
  // allowed while the turn finishes; only sending waits.
  const canType = !!sid && !state.drill && !state.summary && !state.boot

  const sendTurn = async () => {
    const text = draft.trim()
    if (!text || !sid || !state.open) return
    setDraft('')
    dispatch({ type: 'sent', text })
    let problem: string | null = null
    try {
      const r = await api.postTurn(sid, text)
      if (r.status === 409) problem = copyFor(lang).finishFirst
      else if (!r.ok) problem = await api.problem(r)
    } catch (e) {
      problem = String((e as Error).message || e)
    }
    if (problem !== null) {
      setDraft(text)
      dispatch({ type: 'turnFailed', text: problem })
    }
  }

  const skipTask = async () => {
    if (!state.open || !sid || inFlight.current) return
    inFlight.current = true
    try {
      const r = await api.postSkip(sid)
      if (r.status === 409) dispatch({ type: 'banner', text: copyFor(lang).finishFirst })
      else if (r.ok) dispatch({ type: 'toast', text: copyFor(lang).skipped })
    } finally {
      inFlight.current = false
    }
  }

  // The CLI always had `quit`; closing the tab left the session unfinished in
  // the database. End finishes it from any state, the drill included.
  const endSession = async () => {
    if (state.summary && state.reviewing) {        // reading back: End returns to the summary
      dispatch({ type: 'backToSummary' })
      return
    }
    if (!sid) return
    const d = await api.endSession(sid)
    if (!d) return
    dispatch({ type: 'ended', summary: { done: d.tasks_done, outOf: state.header.total, missed: d.tasks_skipped,
                                         progress: d.progress, wordsDue: d.words_due } })
  }

  // Enter then OK sent the answer twice: the second was judged against the
  // NEXT correction and came back "not it yet".
  const sendDrill = async (text: string) => {
    if (!sid || inFlight.current) return
    inFlight.current = true
    try {
      dispatch({ type: 'drillResult', ...(await api.postDrill(sid, text)) })
    } catch (e) {
      dispatch({ type: 'banner', text: String((e as Error).message || e) })
    } finally {
      inFlight.current = false
    }
  }

  return (
    <>
      {!sid && <Setup lang={lang} str={str} loadStrings={loadStrings} onStart={start} />}
      <Boot state={state} />
      <Done state={state} onAgain={() => { setStreamSid(null); start(lang, mode) }}
            onReview={() => dispatch({ type: 'reviewing' })} />

      <Header state={state} endRef={endRef} onSkip={skipTask} onEnd={endSession} />
      <div id="main">
        <div id="convo">
          <Stage state={state} />
          <Transcript log={state.log} drillOpen={!!state.drill} marks={state.marks} art={state.art} />
          {/* One 花丸 per correction retyped right. The pop is decoration,
              shown for a moment by a timer (reduced motion still sees it, just
              without the bounce); a persistent live region says it, because a
              freshly mounted one is often not announced (review #56). */}
          {pop > 0 && (
            <div className="hanamaru-pop" key={pop} aria-hidden="true">
              <Hanamaru size={72} /><span>{copyFor(lang).hanamaru}</span>
            </div>
          )}
          <div className="sr-only" aria-live="polite">{state.hanamaru > 0 ? `${copyFor(lang).hanamaru} ×${state.hanamaru}` : ''}</div>
          {/* Updated once, in full, when an NPC turn completes — "polite", so
              it never cuts off the learner's own screen reader mid-typing. */}
          <div id="srAnnounce" className="sr-only" aria-live="polite" aria-atomic="true">{state.announce}</div>
          <div id="thinking" role="status" className={state.thinking ? 'on' : ''}>
            <i /><i /><i /><span id="thinkingLabel">{state.thinkingLabel}</span>
          </div>
          {state.drill && <Drill drill={state.drill} lang={lang} endRef={endRef} onSubmit={sendDrill} />}
          <footer>
            {/* The placeholder is not a name: it disappears once the learner
                types, and not every screen reader reads it. */}
            <label htmlFor="say" id="sayLabel" className="sr-only">{str.web_input_placeholder || 'Type your reply…'}</label>
            <input type="text" id="say" autoComplete="off" ref={sayRef} disabled={!canType}
                   placeholder={str.web_input_placeholder || 'Type your reply…'} value={draft}
                   onChange={(e) => setDraft(e.target.value)}
                   onKeyDown={(e) => { if (isSubmitKey(e)) sendTurn() }} />
            <button id="send" onClick={sendTurn} disabled={!state.open}>{str.web_send || 'Send'}</button>
          </footer>
        </div>
        <SidePanel state={state} />
      </div>
      <Notices state={state} dispatch={dispatch} />
    </>
  )
}
