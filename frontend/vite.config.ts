import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5621,
    proxy: {
      '/api': {
        target: 'http://localhost:5611',
        changeOrigin: true,
        // Timeout aumentato per dare tempo al backend di avviarsi
        timeout: 10000,
      },
      '/ws': {
        target: 'ws://localhost:5611',
        changeOrigin: true,
        ws: true,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./app"),
    },
  },
})
