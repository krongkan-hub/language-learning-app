import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// Built into app/static/ui and served by FastAPI (app/web/routes.py): the
// page at / and /dashboard, the assets under /ui/. `npm run dev` proxies the
// API to the Python server on :8000. `npm test` runs the Vitest suite in jsdom.
export default defineConfig({
  plugins: [react()],
  base: '/ui/',
  build: { outDir: '../app/static/ui', emptyOutDir: true },
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
  test: { environment: 'jsdom', setupFiles: './src/test-setup.ts' },
})
