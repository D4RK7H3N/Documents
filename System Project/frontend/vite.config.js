const { defineConfig } = require('vite')
const react = require('@vitejs/plugin-react')

module.exports = defineConfig({
  base: './',
  plugins: [react()],
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
    // Same-origin SPA: no sourcemaps in production builds.
    sourcemap: false,
  },
  server: {
    port: 5173,
    // Dev requests are same-origin (http://localhost:5173) and proxied to the
    // local backend, so neither the Electron renderer nor a browser hits CORS:
    // Django only allowlists localhost origins when DEBUG is on, and the
    // gateway Worker keeps ALLOW_DEV=false in production. changeOrigin makes
    // Django see Host localhost:8000, which IS in ALLOWED_HOSTS.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})