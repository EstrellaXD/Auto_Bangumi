<script lang="ts" setup>
import YMenu from './YMenu.vue';

const { status } = storeToRefs(programStore());
</script>

<template>
  <div class="app-layout" w-full h-screen overflow-hidden flex>
    <el-container>
      <el-header
        class="header"
        flex="~ items-center justify-center"
        h-65px
        relative
      >
        <img src="@/assets/logo.png" alt="logo" class="h-7/10" />

        <div absolute right-5 flex="~ items-center" text-3>
          运行状态:
          <div
            class="i-carbon:dot-mark"
            :class="[status ? 'text-green' : 'text-red']"
          ></div>
        </div>
      </el-header>

      <el-container overflow-hidden>
        <el-aside width="auto">
          <YMenu />
        </el-aside>

        <el-main>
          <el-scrollbar>
            <RouterView v-slot="{ Component }">
              <KeepAlive>
                <component :is="Component" />
              </KeepAlive>
            </RouterView>
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
