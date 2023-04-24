import { createApp } from 'vue';
import { Icon } from '@vicons/utils';
import router from './router';
import App from './App.vue';

import '@unocss/reset/tailwind-compat.css';
import 'virtual:uno.css';

const app = createApp(App);
app.component('Icon', Icon);
app.use(router);
app.mount('#app');
