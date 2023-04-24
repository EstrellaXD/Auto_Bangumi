<script lang="ts" setup>
import YMenu from './YMenu.vue';
</script>

<template>
  <div class="app-layout" w-full h-screen overflow-hidden flex>
    <el-container>
      <el-header class="header" flex="~ items-center justify-center" h-65px>
        <img src="@/assets/logo.png" alt="logo" class="h-7/10" />
      </el-header>

      <el-container overflow-hidden>
        <el-aside width="auto">
          <YMenu />
        </el-aside>

        <el-main>
          <el-scrollbar>
            <RouterView />
          </el-scrollbar>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<style lang="scss" scope>
.app-layout {
  @media screen and (max-width: 980px) {
    font-size: 14px;
  }
}

.header {
  border-bottom: 1px solid var(--el-border-color);
}
</style>
