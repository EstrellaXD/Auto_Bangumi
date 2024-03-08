<script lang="ts" setup>
definePage({
  name: 'Index',
  redirect: '/bangumi',
});
</script>

<template>
  <div class="layout-container">
    <ab-topbar />

    <main class="layout-main">
      <ab-sidebar />

      <div class="layout-content">
        <ab-page-title :title="$route.name"></ab-page-title>

        <RouterView v-slot="{ Component }">
          <KeepAlive>
            <component :is="Component" />
          </KeepAlive>
        </RouterView>
      </div>
    </main>
  </div>
</template>

<style lang="scss" scoped>
.layout-container {
  width: 100%;
  height: 100%;
  min-width: 1024px;
  min-height: 768px;
  padding: 16px;

  display: flex;
  flex-direction: column;
  gap: 12px;

  background: #f0f0f0;
}

.layout-main {
  display: flex;
  gap: 20px;

  overflow: hidden;
  height: calc(100vh - 2 * 16px - 60px - 12px);
}

.layout-content {
  overflow: hidden;
  height: 100%;
  display: flex;
  flex-direction: column;
  flex: 1;
}
</style>
