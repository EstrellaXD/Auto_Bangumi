import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
import VueRouter from 'vue-router/vite';
import AutoImport from 'unplugin-auto-import/vite';

export default defineConfig({
  plugins: [
    VueRouter({ dts: false }),
    vue(),
    AutoImport({
      imports: ['vue', 'vitest', 'pinia'],
      dirs: ['src/api', 'src/store', 'src/hooks', 'src/utils'],
      dts: false,
    }),
  ],
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{js,ts}'],
  },
  resolve: { tsconfigPaths: true },
});
