<script setup lang="ts">
import { type GlobalThemeOverrides, NConfigProvider } from 'naive-ui';

const theme: GlobalThemeOverrides = {
  Spin: {
    color: '#fff',
  },
};

const { refresh, isLoggedIn } = useAuth();

if (isLoggedIn.value) {
  refresh();
}
</script>

<template>
  <Suspense>
    <NConfigProvider :theme-overrides="theme">
      <RouterView></RouterView>
    </NConfigProvider>
  </Suspense>
</template>

<style lang="scss">
@import './style/transition';
@import './style/global';
</style>
