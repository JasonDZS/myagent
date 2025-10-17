import { defineConfig } from 'vite';
import path from 'node:path';

export default defineConfig({
  server: { port: 5173 },
  resolve: {
    alias: {
      // Allow importing library source directly for local dev
      '@myagent/ws-console': path.resolve(__dirname, '../src'),
    },
  },
});

