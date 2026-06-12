import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    // Skip the inline module-preload polyfill so the build emits no inline
    // <script>, allowing a strict "script-src 'self'" CSP (set in nginx.conf).
    modulePreload: { polyfill: false },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      // only real feed files go to the backend; /feeds itself is an SPA route
      '^/feeds/.+\\.(txt|json)(\\?.*)?$': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
});
