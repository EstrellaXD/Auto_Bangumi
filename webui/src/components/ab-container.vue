<script lang="ts" setup>
withDefaults(
  defineProps<{
    title: string;
  }>(),
  {
    title: 'title',
  }
);
</script>

<template>
  <div rounded-10 overflow-hidden>
    <div
      bg-theme-row
      w-full
      text-white
      px-20
      h-45
      fx-cer
      justify-between
      select-none
    >
      <div text-h2>{{ title }}</div>

      <slot name="title-right"></slot>
    </div>

    <div p-20 bg-white>
      <slot></slot>
    </div>
  </div>
</template>
