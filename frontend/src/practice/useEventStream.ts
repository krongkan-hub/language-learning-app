import { useEffect, type Dispatch } from 'react'
import type { Action } from './session'
import type { ServerEvent } from './types'

/**
 * Feeds a session's server-sent events into the reducer while `sid` is set.
 *
 * EventSource reconnects on its own, and the server answers an unknown
 * session with 404 — not a transient failure — so without a limit the browser
 * retried immediately, forever, and the tab froze (two were lost that way).
 * A few quiet retries, then give up and say so.
 */
export function useEventStream(sid: string | null, dispatch: Dispatch<Action>): void {
  useEffect(() => {
    if (!sid) return
    const source = new EventSource(`/api/stream/${sid}`)
    let fails = 0
    source.onmessage = (e: MessageEvent<string>) => {
      fails = 0
      dispatch({ type: 'event', ev: JSON.parse(e.data) as ServerEvent })
    }
    source.onerror = () => {
      if (source.readyState === EventSource.CONNECTING && ++fails < 4) {
        dispatch({ type: 'streamLost', fatal: false })
        return
      }
      source.close()
      dispatch({ type: 'streamLost', fatal: true })
    }
    return () => source.close()
  }, [sid, dispatch])
}
