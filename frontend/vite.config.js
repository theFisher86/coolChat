import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/health': 'http://localhost:8000',
      '/chat': 'http://localhost:8000',
      '/config': 'http://localhost:8000',
      '/memory': 'http://localhost:8000',
      '/characters': 'http://localhost:8000',
      '/lore': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test.setup.js',
  },
});
