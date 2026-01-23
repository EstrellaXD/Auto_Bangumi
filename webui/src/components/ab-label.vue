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
  align-items: center;
  justify-content: space-between;
  min-height: 32px;
}

.label-text {
  font-size: 14px;
  color: var(--color-text);
  transition: color var(--transition-normal);
}
</style>
