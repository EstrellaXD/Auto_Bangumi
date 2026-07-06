<script lang="ts" setup>
import { ref } from 'vue';

export interface AbSegmentedOption {
  label: string;
  value: string;
}

// 视图/筛选切换：Soft Ink 下划线标签页（无浮动滑块），方向键可导航。
const props = withDefaults(
  defineProps<{
    options: AbSegmentedOption[];
    size?: 'sm' | 'md';
    ariaLabel?: string;
  }>(),
  {
    size: 'md',
    ariaLabel: undefined,
  }
);

const value = defineModel<string>('value', { required: true });

const tabRefs = ref<HTMLButtonElement[]>([]);

function select(option: AbSegmentedOption) {
  value.value = option.value;
}

function onKeydown(event: KeyboardEvent, index: number) {
  let next: number | null = null;
  if (event.key === 'ArrowRight') next = (index + 1) % props.options.length;
  if (event.key === 'ArrowLeft')
    next = (index - 1 + props.options.length) % props.options.length;
  if (next === null) return;
  event.preventDefault();
  value.value = props.options[next].value;
  tabRefs.value[next]?.focus();
}
</script>

<template>
  <div
    class="ab-segmented"
    :class="`ab-segmented--${size}`"
    role="tablist"
    :aria-label="ariaLabel"
  >
    <button
      v-for="(option, index) in options"
      :key="option.value"
      :ref="(el) => (tabRefs[index] = el as HTMLButtonElement)"
      type="button"
      role="tab"
      class="ab-segmented-tab"
      :class="{ 'ab-segmented-tab--on': option.value === value }"
      :aria-selected="option.value === value"
      :tabindex="option.value === value ? 0 : -1"
      @click="select(option)"
      @keydown="onKeydown($event, index)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style lang="scss" scoped>
.ab-segmented {
  display: inline-flex;
  gap: 16px;
  border-bottom: 1px solid var(--color-border);
}

.ab-segmented-tab {
  padding: 6px 2px;
  margin-bottom: -1px;
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--color-text-secondary);
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: color var(--transition-fast),
    border-color var(--transition-fast);

  @include forTouch {
    padding: 10px 2px;
  }

  &:hover {
    color: var(--color-text);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
    border-radius: 2px;
  }

  &--on {
    color: var(--color-text);
    font-weight: 600;
    border-bottom-color: var(--color-primary);
  }
}

.ab-segmented--sm .ab-segmented-tab {
  font-size: 12px;
  padding: 4px 2px;

  @include forTouch {
    padding: 8px 2px;
  }
}
</style>
