<script lang="ts" setup>
const props = withDefaults(
  defineProps<{
    title: string;
  }>(),
  {
    title: 'title',
  }
);
</script>

<template>
  <div fx-cer space-x-12px>
    <div text-h1>{{ title }}</div>
    <div w-160px h-3px bg-theme-row rounded-full></div>
  </div>
</template>
