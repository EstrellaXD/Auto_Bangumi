import { createRouter, createWebHashHistory } from 'vue-router';

const YLayout = () => import('../pages/YLayout.vue');
const YBangumi = () => import('../pages/bangumi/index.vue');
const YDebug = () => import('../pages/debug/index.vue');

const routes = [
  {
    path: '/',
    component: YLayout,
    redirect: '/bangumi',
    children: [
      {
        path: 'bangumi',
        component: YBangumi
      },
      {
        path: 'debug',
        component: YDebug
      }
    ]
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router;