import type { Dashboard, Language } from './types'

export async function fetchDashboard(language: Language): Promise<Dashboard> {
  const res = await fetch(`/api/dashboard?language=${encodeURIComponent(language)}`)
  if (!res.ok) throw new Error(`dashboard request failed: ${res.status}`)
  return res.json()
}
