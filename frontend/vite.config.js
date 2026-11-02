import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Proxy all /api calls to the FastAPI backend in development
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})

