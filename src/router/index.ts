import { createRouter, createWebHashHistory } from 'vue-router';

const YLayout = () => import('../pages/YLayout.vue');
const YBangumi = () => import('../pages/bangumi/index.vue');
const YDebug = () => import('../pages/debug/index.vue');
const YLog = () => import('../pages/journal/index.vue');
const YConfig = () => import('../pages/config/index.vue');

const routes = [
  {
    path: '/',
    component: YLayout,
    redirect: '/bangumi',
    children: [
      {
        path: 'bangumi',
        component: YBangumi,
      },
      {
        path: 'debug',
        component: YDebug,
      },
      {
        path: 'log',
        component: YLog,
      },
      {
        path: 'config',
        component: YConfig,
      },
    ],
  },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export default router;
