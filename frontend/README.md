# frontend — React + TypeScript (Vite)

The whole web front end, served by the Python app: the practice screen at
`/`, the learner dashboard at `/dashboard`, the built assets under `/ui/`.

    npm install
    npm run dev      # http://127.0.0.1:5173/ui/ (dashboard: /ui/dashboard), proxies /api to :8000
    npm run build    # type-checks (tsc -b), then builds into ../app/static/ui
    npm test         # Vitest + Testing Library, in jsdom

`make web` in the repository root builds this automatically when its sources
change, and `make check` runs the type-check and the tests.

- `src/practice/` — the practice screen. `session.ts` is a pure reducer that
  turns every server event (`app/web/turns.py`) and learner action into
  state; `useEventStream.ts` feeds it the SSE stream; `components/` render
  it; `copy.ts` holds the few lines not in `app/i18n.py`; `practice.css` is
  the stylesheet (its layout and contrast rules are pinned by
  `dev/tests/test_web_ui.py`). Tests sit next to the code (`*.test.ts[x]`),
  with `fakeServer.ts` standing in for the API.
- `src/pages/Dashboard.tsx` + `src/components/` — the dashboard, with
  hand-written SVG charts; `src/api.ts` + `src/types.ts` are the typed
  contract for `GET /api/dashboard` (`app/db/analytics.py`), `src/theme.css`
  its tokens and validated chart palette.

Each page is lazy-loaded with its own stylesheet (`src/App.tsx`), since both
style bare elements like `button` and `table`.
