import { createApp } from 'vue';
import { createPinia } from 'pinia';
import router from './router';
import App from './App.vue';

import '@unocss/reset/tailwind-compat.css';
import 'virtual:uno.css';

import 'element-plus/es/components/message/style/css';
import 'element-plus/es/components/message-box/style/css';

const pinia = createPinia();

const app = createApp(App);
app.use(router);
app.use(pinia);
app.mount('#app');
