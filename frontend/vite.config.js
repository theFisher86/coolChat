import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
    '/plugins': 'http://127.0.0.1:8001',
    '/plugins/static': 'http://127.0.0.1:8001',
        '/health': 'http://127.0.0.1:8001',
        '/chat': 'http://127.0.0.1:8001',
        '/config': 'http://127.0.0.1:8001',
        '/theme': 'http://127.0.0.1:8001',
        '/models': 'http://127.0.0.1:8001',
        '/memory': 'http://127.0.0.1:8001',
        '/characters': 'http://127.0.0.1:8001',
        '/lore': 'http://127.0.0.1:8001',
        '/public': 'http://127.0.0.1:8001',
        '/lorebooks': 'http://127.0.0.1:8001',
        '/image': 'http://127.0.0.1:8001',
        '/images': 'http://127.0.0.1:8001',
        '/prompts': 'http://127.0.0.1:8001',
        '/chats': 'http://127.0.0.1:8001',
        '/themes': 'http://127.0.0.1:8001',
        '/phone': 'http://127.0.0.1:8001',
        '/tools': 'http://127.0.0.1:8001',
      },
    host: '0.0.0.0',
    allowedHosts: ['fisher7865.ddns.net']
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test.setup.js',
  },
});
