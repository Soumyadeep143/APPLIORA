import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In local dev, API calls to /api and /health are proxied to the FastAPI
// backend on :8000. In production set VITE_API_URL to the backend origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
