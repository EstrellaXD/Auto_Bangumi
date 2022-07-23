<script setup lang="ts">
import { Home, Debug } from '@vicons/carbon';
</script>

<template>
  <ElMenu
    default-active="/bangumi"
    class="app-menu"
    router
  >

    <ElMenuItem index="/bangumi">
      <Icon>
        <Home />
      </Icon>
      <template #title>番剧管理</template>
    </ElMenuItem>

    <ElMenuItem index="/debug">
      <Icon>
        <Debug />
      </Icon>
      <template #title>调试</template>
    </ElMenuItem>

  </ElMenu>
</template>

<style lang='scss' scope>
.app-menu {
  height: 100%;

  .xicon{
    margin-right: .5em;
  }
}
</style>