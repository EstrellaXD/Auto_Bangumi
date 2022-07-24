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

      <el-container style="overflow: hidden;">
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

<style lang='scss' scope>
.app-layout {
  width: 100%;
  height: 100vh;
  overflow: hidden;
  display: flex;

  @media screen and (max-width: 980px){
    font-size: 14px;
  }
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