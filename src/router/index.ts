import { createRouter, createWebHashHistory } from 'vue-router';

const YLayout = () => import('../pages/YLayout.vue');
const YBangumi = () => import('../pages/YBangumi.vue');
const YDebug = () => import('../pages/YDebug.vue');

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