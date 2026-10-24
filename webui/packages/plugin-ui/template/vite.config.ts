// 前端插件组件的 Vite 库模式模板。
//
// 把本目录复制到插件根目录下（如 my-plugin/web-src/），把 package.json 中
// @autobangumi/plugin-ui 的 link: 路径改为指向 webui/packages/plugin-ui，
// 然后 `pnpm install && pnpm build`，产物写到插件的 web/index.js，
// 清单中对应写 `entry = "web/index.js"`。
//
// 产物必须是单个自包含的 ES module：浏览器里没有裸模块名解析，CSP
// （script-src 'self'）也不允许 import map 等内联脚本与远程脚本，
// 所以依赖全部打包进来，不设 external。
import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    lib: {
      entry: 'src/index.ts',
      formats: ['es'],
      fileName: () => 'index.js',
    },
    outDir: '../web',
    emptyOutDir: true,
  },
});
