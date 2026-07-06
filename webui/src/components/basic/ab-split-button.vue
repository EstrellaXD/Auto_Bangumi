<script lang="ts" setup>
import { Down } from '@icon-park/vue-next';
import AbMenu from './ab-menu.vue';
import type { AbMenuItem } from './ab-menu.vue';

export interface AbSplitOption {
  label: string;
  value: string;
}

// 分体按钮：主区执行当前选项，箭头打开选项菜单（替代旧 ab-button-multi）。
// 选中项通过 v-model:value 受控，不再内部私藏状态。
const props = withDefaults(
  defineProps<{
    options: AbSplitOption[];
    loading?: boolean;
    disabled?: boolean;
    size?: 'sm' | 'md';
  }>(),
  {
    loading: false,
    disabled: false,
    size: 'md',
  }
);

const value = defineModel<string>('value', { required: true });

const emit = defineEmits<{ click: [value: string] }>();

const selected = computed(
  () =>
    props.options.find((option) => option.value === value.value) ??
    props.options[0]
);

const menuItems = computed<AbMenuItem[]>(() =>
  props.options.map((option) => ({
    key: option.value,
    label: option.label,
    handler: () => {
      value.value = option.value;
    },
  }))
);

function onMainClick() {
  if (props.disabled || props.loading) return;
  emit('click', selected.value.value);
}
</script>

<template>
  <div class="ab-split" :class="`ab-split--${size}`">
    <button
      type="button"
      class="ab-split-main"
      :disabled="disabled || loading"
      :aria-busy="loading || undefined"
      @click="onMainClick"
    >
      <span v-if="loading" class="ab-split-spin" aria-hidden="true"></span>
      {{ selected?.label }}
    </button>

    <ab-menu :items="menuItems" align="right">
      <template #trigger>
        <button
          type="button"
          class="ab-split-arrow"
          :disabled="disabled || loading"
          :aria-label="$t('common.moreActions')"
        >
          <Down size="12" />
        </button>
      </template>
    </ab-menu>
  </div>
</template>

<style lang="scss" scoped>
.ab-split {
  display: inline-flex;
  border-radius: var(--radius-sm);

  &--md {
    height: 34px;
    font-size: 14px;

    @include forTouch {
      height: var(--touch-target);
    }
  }

  &--sm {
    height: 28px;
    font-size: 13px;

    @include forTouch {
      height: 36px;
    }
  }
}

.ab-split-main,
.ab-split-arrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  border: none;
  background: var(--color-primary);
  color: var(--color-white);
  font-family: inherit;
  font-size: inherit;
  font-weight: 500;
  cursor: pointer;
  transition: background-color var(--transition-fast);

  &:hover:not(:disabled) {
    background: var(--color-primary-hover);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
}

.ab-split-main {
  gap: 7px;
  padding: 0 14px;
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
}

.ab-split-arrow {
  width: 30px;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  border-left: 1px solid color-mix(in srgb, var(--color-white) 28%, transparent);
}

.ab-split-spin {
  width: 13px;
  height: 13px;
  flex-shrink: 0;
  border-radius: 50%;
  border: 2px solid color-mix(in srgb, currentColor 35%, transparent);
  border-top-color: currentColor;
  animation: ab-split-rotate 0.7s linear infinite;

  @media (prefers-reduced-motion: reduce) {
    animation-duration: 1.6s;
  }
}

@keyframes ab-split-rotate {
  to {
    transform: rotate(360deg);
  }
}
</style>
