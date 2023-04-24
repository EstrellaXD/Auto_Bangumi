<script setup lang="ts">
import { useRoute } from 'vue-router';
import { Debug, DocumentBlank, Home } from '@vicons/carbon';
import { useWindowSize } from '@vueuse/core';

const { fullPath } = useRoute();

const isCollapse = ref(false);

const { width } = useWindowSize();
const WIDTH = 980;

watchEffect(() => {
  if (width.value < WIDTH) {
    isCollapse.value = true;
  } else {
    isCollapse.value = false;
  }
});
</script>

<template>
  <el-menu
    class="app-menu"
    :default-active="fullPath"
    :collapse="isCollapse"
    router
  >
    <el-menu-item index="/bangumi">
      <Icon>
        <Home />
      </Icon>
      <template #title>番剧管理</template>
    </el-menu-item>

    <el-menu-item index="/debug">
      <Icon>
        <Debug />
      </Icon>
      <template #title>调试</template>
    </el-menu-item>
    <el-menu-item index="/log">
      <Icon>
        <DocumentBlank />
      </Icon>
      <template #title>日志</template>
    </el-menu-item>
  </el-menu>
</template>

<style lang="scss" scope>
.app-menu {
  height: 100%;

  .xicon {
    margin-right: 0.5em;
  }
}
</style>
