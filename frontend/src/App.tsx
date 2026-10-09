import { lazy, Suspense } from 'react'

// Two pages, each a separate navigation with its own stylesheet: the practice
// screen at /, the learner dashboard at /dashboard. Loaded lazily so a page
// never carries the other's CSS (both style bare elements like button and table).
const Practice = lazy(() => import('./practice/Practice').then((m) => ({ default: m.Practice })))
const Dashboard = lazy(() => import('./pages/Dashboard').then((m) => ({ default: m.Dashboard })))

// The art review pages exist only under `npm run dev` (/ui/gallery, /ui/scenes).
// The imports themselves sit behind the DEV constant: a lazy() at module level
// with only the render guarded still emitted the chunk into the build.
const DEV_PAGES = import.meta.env.DEV
  ? {
      gallery: lazy(() => import('./art/Gallery').then((m) => ({ default: m.Gallery }))),
      scenes: lazy(() => import('./art/SceneGallery').then((m) => ({ default: m.SceneGallery }))),
    }
  : null

export default function App() {
  // /dashboard in production, /ui/dashboard under `npm run dev` (base /ui/)
  const onDashboard = /\/dashboard\/?$/.test(window.location.pathname)
  const devPage = DEV_PAGES && /\/(gallery|scenes)\/?$/.exec(window.location.pathname)?.[1]
  if (DEV_PAGES && devPage) {
    const Page = DEV_PAGES[devPage as keyof typeof DEV_PAGES]
    return <Suspense fallback={null}><Page /></Suspense>
  }
  return <Suspense fallback={null}>{onDashboard ? <Dashboard /> : <Practice />}</Suspense>
}
