import { resolve } from 'node:path';
import UnoCSS from 'unocss/vite';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import AutoImport from 'unplugin-auto-import/vite';
import Components from 'unplugin-vue-components/vite';
import VueRouter from 'vue-router/vite';
import { VueRouterAutoImports } from 'vue-router/unplugin';
import VueI18nPlugin from '@intlify/unplugin-vue-i18n/vite';

// 与后端给 SPA 文档加的响应头一致（backend/src/main.py）。只加在 preview：
// dev 服务器会注入内联脚本，会被这个策略拦下
const headers = { 'Content-Security-Policy': 'script-src \'self\'' };

// https://vitejs.dev/config/
export default defineConfig({
  base: './',
  plugins: [
    VueRouter({
      dts: 'types/dts/router-type.d.ts',
    }),
    vue(),
    UnoCSS(),
    AutoImport({
      imports: [
        'vue',
        'pinia',
        {
          '@vueuse/core': [
            'createSharedComposable',
            'useBreakpoints',
            'usePreferredDark',
            'useClipboard',
            'useLocalStorage',
            'useIntervalFn',
          ],
        },
        VueRouterAutoImports,
        'vue-i18n',
      ],
      dts: 'types/dts/auto-imports.d.ts',
      dirs: ['src/api', 'src/store', 'src/hooks', 'src/utils'],
    }),
    Components({
      dts: 'types/dts/components.d.ts',
    }),
    VueI18nPlugin({
      include: resolve(import.meta.dirname, './src/i18n/**'),
      dropMessageCompiler: true,
    }),
  ],
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: '@use "@/style/mixin.scss" as *;',
      },
    },
  },
  build: {
    cssCodeSplit: false,
    rolldownOptions: {
      output: { minify: { compress: { dropConsole: true } } },
    },
  },
  resolve: {
    tsconfigPaths: true,
    // 只用运行时：模板都在构建期编译，不需要打包 @vue/compiler-*
    alias: [
      { find: /^vue$/, replacement: 'vue/dist/vue.runtime.esm-bundler.js' },
    ],
  },
  preview: { headers },
  server: {
    proxy: {
      '^/api/.*': {
        target: 'http://localhost:7892',
        changeOrigin: false,
      },
      '^/posters/.*': 'http://localhost:7892',
    },
  },
});
