<script setup lang="ts">
import { NMessageProvider } from 'naive-ui';
</script>

<template>
  <Suspense>
    <NMessageProvider>
      <RouterView></RouterView>
    </NMessageProvider>
  </Suspense>
</template>

<style lang="scss">
@import './style/transition';
@import './style/global';
</style>
