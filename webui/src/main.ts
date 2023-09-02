import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { router } from './router';
import App from './App.vue';

import '@unocss/reset/tailwind-compat.css';
import 'virtual:uno.css';

const pinia = createPinia();
const { i18n } = useMyI18n();

if (window.matchMedia('(display-mode: standalone)').matches) {
  console.log('网页以 "standalone" 模式运行');
  if('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
      .then(() => { console.log('Service Worker Registered'); });
  }
} else {
  console.log('网页未以 "standalone" 模式运行');
}


const app = createApp(App);
app.use(router);
app.use(pinia);
app.use(i18n);
app.mount('#app');
