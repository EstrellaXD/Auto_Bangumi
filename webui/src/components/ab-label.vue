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
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  min-height: 32px;

  @include forTablet {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  // Make inputs full-width on mobile
  :deep(input[ab-input]),
  :deep(.ab-select),
  :deep(.n-dynamic-tags) {
    width: 100%;

    @include forTablet {
      width: auto;
      min-width: 200px;
    }
  }
}

.label-text {
  font-size: 14px;
  color: var(--color-text);
  transition: color var(--transition-normal);
  flex-shrink: 0;
}
</style>
