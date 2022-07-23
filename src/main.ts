import { createApp } from 'vue'
import App from './App.vue'
import 'vue-global-api'
import 'modern-normalize/modern-normalize.css'
import router from './router';
import { Icon } from '@vicons/utils'

const app = createApp(App)

app.component('Icon', Icon);

app.use(router)

app.mount('#app')
