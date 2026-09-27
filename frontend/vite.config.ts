import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Built into app/static/ui and served by FastAPI at /ui/ (app/web/routes.py).
// `npm run dev` proxies the API to the Python server on :8000.
export default defineConfig({
  plugins: [react()],
  base: '/ui/',
  build: { outDir: '../app/static/ui', emptyOutDir: true },
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
})
