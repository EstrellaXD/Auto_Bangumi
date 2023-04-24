<script setup lang="ts">
import { useWindowSize } from '@vueuse/core';

const { fullPath } = useRoute();
const { width } = useWindowSize();
const isCollapse = ref(false);
const WIDTH = 980;

watchEffect(() => {
  if (width.value < WIDTH) {
    isCollapse.value = true;
  } else {
    isCollapse.value = false;
  }
});

const items = [
  {
    icon: 'i-carbon-home',
    title: '番剧管理',
    url: '/bangumi',
  },
  {
    icon: 'i-carbon-debug',
    title: '调试',
    url: '/debug',
  },
  {
    icon: 'i-carbon:align-box-middle-right',
    title: '日志',
    url: '/log',
  },
  {
    icon: 'i-carbon:settings',
    title: '配置',
    url: '/config',
  },
];
</script>

<template>
  <el-menu :default-active="fullPath" :collapse="isCollapse" router h-full>
    <template v-for="(i, index) in items" :key="index">
      <el-menu-item :index="i.url">
        <div :class="[i.icon]" mr-0.5em></div>
        <template #title>{{ i.title }}</template>
      </el-menu-item>
    </template>
  </el-menu>
</template>
