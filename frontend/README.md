# frontend — React + TypeScript (Vite)

The learner dashboard, served by the Python app at `/ui/`.

    npm install
    npm run dev      # http://127.0.0.1:5173/ui/, proxies /api to the Python server on :8000
    npm run build    # type-checks (tsc -b), then builds into ../app/static/ui

`make web` in the repository root builds this automatically when its sources
change. Layout: `src/pages/` (screens), `src/components/` (stat tiles and
hand-written SVG charts), `src/api.ts` + `src/types.ts` (the typed contract
for `GET /api/dashboard`, produced by `app/db/analytics.py`), `src/theme.css`
(the app's dark-theme tokens and the validated chart palette).
