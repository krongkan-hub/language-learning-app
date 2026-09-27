// A reload used to throw the session away: the id lived only in a variable,
// so the page came back to the home screen while the server went on holding
// the session — a playtest lost an explain session at 1/5 that way.
// sessionStorage is the right scope: it survives a reload and dies with the
// tab. Wrapped because a browser set to block site data throws on access.
const RESUME_KEY = 'coach.sid'

export function remember(sid: string | null): void {
  try {
    if (sid) sessionStorage.setItem(RESUME_KEY, sid)
    else sessionStorage.removeItem(RESUME_KEY)
  } catch { /* storage blocked: resume just won't be offered */ }
}

export function remembered(): string | null {
  try {
    return sessionStorage.getItem(RESUME_KEY)
  } catch {
    return null
  }
}
