import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      // only real feed files go to the backend; /feeds itself is an SPA route
      '^/feeds/.+\\.(txt|json)(\\?.*)?$': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
});
