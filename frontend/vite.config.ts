/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Публичный доступ через туннель: разрешаем домены туннелей,
    // иначе Vite отклоняет запросы с чужим Host (403 Blocked request).
    allowedHosts: ['.serveousercontent.com', '.trycloudflare.com', '.lhr.life', '.localhost.run'],
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
});
