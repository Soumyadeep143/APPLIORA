import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Temporary, verification-only config (deleted after manual QA) — proxies
// to an isolated backend instance on :8001 (scratch DB) instead of the
// shared :8000 dev server, so this check can't collide with anything else
// already running.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5300,
    strictPort: true,
    proxy: {
      '/api': 'http://localhost:8001',
      '/health': 'http://localhost:8001',
    },
  },
})
