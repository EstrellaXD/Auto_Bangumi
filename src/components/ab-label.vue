<script lang="ts" setup>
const props = withDefaults(
  defineProps<{
    label: string;
  }>(),
  {
    label: '',
  }
);
</script>

<template>
  <div flex="~ items-start" justify-between>
    <div>{{ label }}</div>

    <slot> </slot>
  </div>
</template>
