import { resolve } from 'node:path';
import UnoCSS from 'unocss/vite';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import AutoImport from 'unplugin-auto-import/vite';
import Components from 'unplugin-vue-components/vite';
import VueRouter from 'unplugin-vue-router/vite';
import { VueRouterAutoImports } from 'unplugin-vue-router';
import { HeadlessUiResolver } from 'unplugin-vue-components/resolvers';

// https://vitejs.dev/config/
export default defineConfig({
  base: './',
  plugins: [
    VueRouter({
      dts: 'src/router-type.d.ts',
    }),
    vue(),
    UnoCSS(),
    AutoImport({
      imports: ['vue', 'vitest', 'pinia', '@vueuse/core', VueRouterAutoImports],
      dts: 'src/auto-imports.d.ts',
      dirs: ['src/api', 'src/store', 'src/hooks'],
    }),
    Components({
      dts: 'src/components.d.ts',
      dirs: ['src/basic'],
      resolvers: [HeadlessUiResolver()],
    }),
  ],
  build: {
    cssCodeSplit: false,
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '#': resolve(__dirname, 'types'),
    },
  },
  server: {
    host: '0.0.0.0',
    proxy: {
      '^api/.*': 'http://126.0.0.1:7892',
    },
  },
});
