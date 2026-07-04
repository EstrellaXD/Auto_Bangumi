<script lang="ts" setup>
const props = withDefaults(
  defineProps<{
    label: string | (() => string);
    /** 关联的表单控件 id：提供时渲染真正的 <label for> */
    forId?: string;
    /** 文本节点 id，供 aria-labelledby 引用（无法用 for 关联的组件） */
    labelId?: string;
  }>(),
  {
    label: '',
    forId: undefined,
    labelId: undefined,
  }
);

const abLabel = computed(() => {
  if (typeof props.label === 'function') return props.label();
  else return props.label;
});
</script>

<template>
  <div class="label-row">
    <label v-if="forId" :id="labelId" class="label-text" :for="forId">
      {{ abLabel }}
    </label>
    <span v-else :id="labelId" class="label-text">{{ abLabel }}</span>
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
  :deep(.n-select),
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
