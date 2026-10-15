import { useEffect, useState } from 'react'
import { fetchToday, type Today } from './api'
import type { Language } from './types'

/**
 * GET /api/today for one language, fetched again whenever `lang` or `key`
 * changes; null while it loads, or when `lang` is null. A failed fetch is an
 * empty page, not an error: Today's page still offers a conversation.
 */
export function useToday(lang: Language | null, key: unknown = null): Today | null {
  const [data, setData] = useState<Today | null>(null)
  useEffect(() => {
    let live = true
    setData(null)
    if (!lang) return
    fetchToday(lang).then((d) => { if (live) setData(d) })
      .catch(() => { if (live) setData({ review: [], recent: [], done_today: 0, streak: 0 }) })
    return () => { live = false }
  }, [lang, key])
  return data
}
