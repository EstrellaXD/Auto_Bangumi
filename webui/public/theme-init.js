// 渲染前应用深色模式，避免闪烁。CSP 为 script-src 'self'，不能写成内联脚本。
(function () {
  const saved = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  if (saved === 'dark' || (!saved && prefersDark))
    document.documentElement.classList.add('dark');
})();
