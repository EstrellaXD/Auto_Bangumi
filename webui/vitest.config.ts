import { resolve } from 'node:path';
import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
import AutoImport from 'unplugin-auto-import/vite';

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      imports: ['vue', 'vitest', 'pinia'],
      dts: false,
    }),
  ],
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{js,ts}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{ts,vue}'],
      exclude: [
        'src/test/**',
        'src/**/*.d.ts',
        'src/main.ts',
        'src/router/**',
      ],
    },
  },
  resolve: {
    alias: {
      '~': resolve(__dirname, './'),
      '@': resolve(__dirname, 'src'),
      '#': resolve(__dirname, 'types'),
    },
  },
});
