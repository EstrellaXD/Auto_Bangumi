<script lang="ts" setup>
withDefaults(
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
