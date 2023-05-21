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
  <div rounded-10px overflow-hidden>
    <div
      bg-theme-row
      w-full
      text-white
      fx-cer
      px-20px
      h-45px
      justify-between
      select-none
    >
      <div text-h2>{{ title }}</div>
    </div>

    <div p-20px bg-white>
      <slot></slot>
    </div>
  </div>
</template>
