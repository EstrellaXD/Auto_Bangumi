<script lang="ts" setup>
const props = withDefaults(
  defineProps<{
    label: string | (() => string);
  }>(),
  {
    label: '',
  }
);

const abLabel = computed(() => {
  if (typeof props.label === 'function') return props.label();
  else return props.label;
});
</script>

<template>
  <div class="label-row">
    <div class="label-text">{{ abLabel }}</div>
    <slot></slot>
  </div>
</template>

<style lang="scss" scoped>
.label-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.label-text {
  font-size: 14px;
  color: var(--color-text);
  padding-top: 4px;
  transition: color var(--transition-normal);
}
</style>
