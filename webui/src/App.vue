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

const { refresh, isLoggedin } = useAuth();
if (isLoggedin.value === true) {
  refresh();
}
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
