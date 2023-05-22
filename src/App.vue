<script setup lang="ts"></script>

<template>
  <Suspense>
    <div layout-container>
      <ab-topbar />

      <main layout-main>
        <ab-sidebar />

        <div layout-content>
          <ab-page-title :title="$route.name"></ab-page-title>

          <div overflow-auto mt-12px flex-grow>
            <RouterView v-slot="{ Component }">
              <KeepAlive>
                <component :is="Component" />
              </KeepAlive>
            </RouterView>
          </div>
        </div>
      </main>
    </div>
  </Suspense>
</template>

<style lang="scss">
@import './style/transition';
@import './style/global';
</style>
