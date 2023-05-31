<script setup lang="ts">
import {
  type GlobalThemeOverrides,
  NConfigProvider,
  NMessageProvider,
} from 'naive-ui';

const theme: GlobalThemeOverrides = {
  Spin: {
    color: '#fff',
  },
};

const { refresh } = useAuth();
refresh();
</script>

<template>
  <Suspense>
    <NConfigProvider :theme-overrides="theme">
      <NMessageProvider>
        <RouterView></RouterView>
      </NMessageProvider>
    </NConfigProvider>
  </Suspense>
</template>

<style lang="scss">
@import './style/transition';
@import './style/global';
</style>
