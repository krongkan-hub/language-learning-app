import { lazy, Suspense } from 'react'

// Two pages, each a separate navigation with its own stylesheet: the practice
// screen at /, the learner dashboard at /dashboard. Loaded lazily so a page
// never carries the other's CSS (both style bare elements like button and table).
const Practice = lazy(() => import('./practice/Practice').then((m) => ({ default: m.Practice })))
const Dashboard = lazy(() => import('./pages/Dashboard').then((m) => ({ default: m.Dashboard })))

export default function App() {
  // /dashboard in production, /ui/dashboard under `npm run dev` (base /ui/)
  const onDashboard = /\/dashboard\/?$/.test(window.location.pathname)
  return <Suspense fallback={null}>{onDashboard ? <Dashboard /> : <Practice />}</Suspense>
}
