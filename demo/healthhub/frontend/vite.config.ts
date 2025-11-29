import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.VITE_API_BASE_URL || 'http://localhost:8850'

  return {
    plugins: [react()],
    build: {
      outDir: 'build',  // Match ShipNorth pattern (not 'dist')
    },
    server: {
      port: 5173,
      host: true,
      allowedHosts: true,  // Allow all hosts for Docker networking
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
