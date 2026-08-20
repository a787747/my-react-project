import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const devApiProxy = process.env.VITE_DEV_API_PROXY

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  ...(devApiProxy
    ? {
        server: {
          proxy: {
            '/webhook': {
              target: devApiProxy,
              changeOrigin: true,
            },
          },
        },
      }
    : {}),
})
