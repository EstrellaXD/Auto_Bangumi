import {createApp} from 'vue';
import {createPinia} from 'pinia';
import {router} from './router';
import App from './App.vue';

import '@unocss/reset/tailwind-compat.css';
import 'virtual:uno.css';

const pinia = createPinia();
const {i18n} = useMyI18n();



const app = createApp(App);
app.use(router);
app.use(pinia);
app.use(i18n);
app.mount('#app');
