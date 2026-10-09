import { lazy, Suspense } from 'react'

// Two pages, each a separate navigation with its own stylesheet: the practice
// screen at /, the learner dashboard at /dashboard. Loaded lazily so a page
// never carries the other's CSS (both style bare elements like button and table).
const Practice = lazy(() => import('./practice/Practice').then((m) => ({ default: m.Practice })))
const Dashboard = lazy(() => import('./pages/Dashboard').then((m) => ({ default: m.Dashboard })))
// The art review page exists only under `npm run dev` (/ui/gallery). The
// import itself sits behind the DEV constant: a lazy() at module level with
// only the render guarded still emitted the Gallery chunk into the build.
const Gallery = import.meta.env.DEV
  ? lazy(() => import('./art/Gallery').then((m) => ({ default: m.Gallery })))
  : null

export default function App() {
  // /dashboard in production, /ui/dashboard under `npm run dev` (base /ui/)
  const onDashboard = /\/dashboard\/?$/.test(window.location.pathname)
  if (Gallery && /\/gallery\/?$/.test(window.location.pathname)) {
    return <Suspense fallback={null}><Gallery /></Suspense>
  }
  return <Suspense fallback={null}>{onDashboard ? <Dashboard /> : <Practice />}</Suspense>
}
