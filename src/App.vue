<script setup lang="ts">
import { NMessageProvider } from 'naive-ui';
</script>

<template>
  <Suspense>
    <n-message-provider>
      <RouterView></RouterView>
    </n-message-provider>
  </Suspense>
</template>

<style lang="scss">
@import './style/transition';
@import './style/global';
</style>
