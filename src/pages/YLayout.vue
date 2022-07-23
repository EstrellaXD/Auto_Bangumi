<script setup lang="ts">
import YMenu from './YMenu.vue';
</script>

<template>
  <div class="app-layout">
    <el-container>
      <el-header class="header">
        <img
          src="@/assets/logo.png"
          alt="logo"
          class="logo"
        >
      </el-header>

      <el-container>
        <el-aside width="200px">
          <YMenu />
        </el-aside>

        <el-main>
          <RouterView />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<style lang='scss' scope>
.app-layout {
  width: 100%;
  height: 100vh;
  overflow: hidden;
  display: flex;
}

.header {
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--el-border-color);
  height: 65px;

  .logo {
    height: 70%;
  }
}
</style>