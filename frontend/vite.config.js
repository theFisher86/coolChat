import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/health': 'http://127.0.0.1:8000',
      '/chat': 'http://127.0.0.1:8000',
      '/config': 'http://127.0.0.1:8000',
      '/models': 'http://127.0.0.1:8000',
      '/memory': 'http://127.0.0.1:8000',
      '/characters': 'http://127.0.0.1:8000',
      '/lore': 'http://127.0.0.1:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test.setup.js',
  },
});
