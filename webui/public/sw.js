// ponytail: 自毁 SW，清理 2023-09 前注册的旧 SW；4.1 删除本文件
// 旧版 vite-plugin-pwa 注册的 SW 仍会按 /sw.js 检查更新，取到本文件后：
// 清空它留下的缓存、注销自己，再让它控制的页面重新加载，回到无 SW 的普通请求
self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.map((key) => caches.delete(key)));
      await self.registration.unregister();
      const clients = await self.clients.matchAll({ type: 'window' });
      clients.forEach((client) => client.navigate(client.url));
    })()
  );
});
