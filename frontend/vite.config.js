import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
  '/plugins': 'http://127.0.0.1:8000',
  '/plugins/static': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/chat': 'http://127.0.0.1:8000',
      '/config': 'http://127.0.0.1:8000',
      '/theme': 'http://127.0.0.1:8000',
      '/models': 'http://127.0.0.1:8000',
      '/memory': 'http://127.0.0.1:8000',
      '/characters': 'http://127.0.0.1:8000',
      '/lore': 'http://127.0.0.1:8000',
      '/public': 'http://127.0.0.1:8000',
      '/lorebooks': 'http://127.0.0.1:8000',
      '/image': 'http://127.0.0.1:8000',
      '/images': 'http://127.0.0.1:8000',
      '/prompts': 'http://127.0.0.1:8000',
      '/chats': 'http://127.0.0.1:8000',
      '/themes': 'http://127.0.0.1:8000',
      '/phone': 'http://127.0.0.1:8000',
      '/tools': 'http://127.0.0.1:8000',
    },
    host: '0.0.0.0',
    allowedHosts: ['fisher7865.ddns.net']
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test.setup.js',
  },
});
