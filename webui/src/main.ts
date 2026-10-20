import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { router } from './router';
import { i18n, loadSavedLocale } from './hooks/useMyI18n';
import App from './App.vue';

import '@unocss/reset/tailwind-compat.css';
import 'virtual:uno.css';

const pinia = createPinia();

const app = createApp(App);
app.use(router);
app.use(pinia);
app.use(i18n);
// 已保存的语言包加载完再渲染，避免先闪出英文
loadSavedLocale().then(() => app.mount('#app'));
