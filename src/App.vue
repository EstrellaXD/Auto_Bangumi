<script setup lang="ts">
import {
  NMessageProvider,
  NConfigProvider,
  type GlobalThemeOverrides,
} from 'naive-ui';

const theme: GlobalThemeOverrides = {
  Spin: {
    color: '#fff',
  },
};
</script>

<template>
  <Suspense>
    <n-config-provider :theme-overrides="theme">
      <n-message-provider>
        <RouterView></RouterView>
      </n-message-provider>
    </n-config-provider>
  </Suspense>
</template>

<style lang="scss">
@import './style/transition';
@import './style/global';
</style>
