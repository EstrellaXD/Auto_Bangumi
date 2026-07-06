<script lang="ts" setup>
import { computed, inject, ref } from 'vue';
import { abFieldInjectionKey } from './ab-field.vue';

// 文本输入组件（取代 UnoCSS 的 ab-input 快捷类）：
// Soft Ink 填充式，左对齐；支持前后缀、清空、密码可见切换、错误态。
const props = withDefaults(
  defineProps<{
    type?: 'text' | 'password' | 'number' | 'url' | 'search';
    placeholder?: string;
    disabled?: boolean;
    clearable?: boolean;
    /** 错误态样式；错误文案由外层 ab-field 显示 */
    error?: boolean;
    ariaLabel?: string;
    min?: number;
    max?: number;
    step?: number;
  }>(),
  {
    type: 'text',
    placeholder: '',
    disabled: false,
    clearable: false,
    error: false,
    ariaLabel: undefined,
    min: undefined,
    max: undefined,
    step: undefined,
  }
);

const model = defineModel<string | number>({ default: '' });

const field = inject(abFieldInjectionKey, null);

const revealed = ref(false);

const effectiveType = computed(() => {
  if (props.type === 'password') return revealed.value ? 'text' : 'password';
  return props.type;
});

const invalid = computed(() => props.error || field?.invalid.value === true);

function onInput(event: Event) {
  const value = (event.target as HTMLInputElement).value;
  model.value = props.type === 'number' && value !== '' ? Number(value) : value;
}

function clear() {
  model.value = '';
}
</script>

<template>
  <span
    class="ab-input"
    :class="{
      'ab-input--error': invalid,
      'ab-input--disabled': disabled,
    }"
  >
    <span v-if="$slots.prefix" class="ab-input-affix">
      <slot name="prefix"></slot>
    </span>

    <input
      :id="field?.controlId"
      :value="model"
      :type="effectiveType"
      :placeholder="placeholder"
      :disabled="disabled"
      :min="min"
      :max="max"
      :step="step"
      :aria-label="ariaLabel"
      :aria-describedby="field?.describedBy.value"
      :aria-invalid="invalid || undefined"
      @input="onInput"
    />

    <button
      v-if="clearable && String(model).length > 0 && !disabled"
      type="button"
      class="ab-input-clear"
      :aria-label="$t('common.clear')"
      tabindex="-1"
      @click="clear"
    >
      <svg viewBox="0 0 24 24" fill="none" width="12" height="12">
        <path
          d="M6 6l12 12M18 6 6 18"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
        />
      </svg>
    </button>

    <button
      v-if="type === 'password'"
      type="button"
      class="ab-input-reveal"
      :aria-pressed="revealed"
      :aria-label="$t('common.toggle_password')"
      @click="revealed = !revealed"
    >
      <svg
        v-if="revealed"
        viewBox="0 0 24 24"
        fill="none"
        width="14"
        height="14"
      >
        <path
          d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6Z"
          stroke="currentColor"
          stroke-width="2"
          stroke-linejoin="round"
        />
        <circle cx="12" cy="12" r="2.5" stroke="currentColor" stroke-width="2" />
      </svg>
      <svg v-else viewBox="0 0 24 24" fill="none" width="14" height="14">
        <path
          d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6Z"
          stroke="currentColor"
          stroke-width="2"
          stroke-linejoin="round"
        />
        <path
          d="M4 4l16 16"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        />
      </svg>
    </button>

    <span v-if="$slots.suffix" class="ab-input-affix">
      <slot name="suffix"></slot>
    </span>
  </span>
</template>

<style lang="scss" scoped>
.ab-input {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  height: 36px;
  padding: 0 11px;
  background: var(--color-surface-2);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  transition: border-color var(--transition-fast),
    background-color var(--transition-fast), box-shadow var(--transition-fast);

  @include forTablet {
    width: 200px;
    height: 30px;
  }

  &:focus-within {
    background: var(--color-surface);
    border-color: var(--color-primary);
    box-shadow: 0 0 0 2px var(--color-primary-alpha);
  }

  &--error {
    border-color: var(--color-danger);

    &:focus-within {
      border-color: var(--color-danger);
      box-shadow: 0 0 0 2px
        color-mix(in srgb, var(--color-danger) 20%, transparent);
    }
  }

  &--disabled {
    opacity: 0.55;
  }

  input {
    flex: 1;
    min-width: 0;
    border: none;
    outline: none;
    background: transparent;
    color: var(--color-text);
    font-family: inherit;
    font-size: 13px;
    padding: 0;

    &::placeholder {
      color: var(--color-text-secondary);
      opacity: 0.85;
    }

    &:disabled {
      cursor: not-allowed;
    }
  }
}

.ab-input-affix {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  color: var(--color-text-muted);
  font-size: 12px;
}

.ab-input-clear,
.ab-input-reveal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  padding: 0;
  border: none;
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: color var(--transition-fast);

  &:hover {
    color: var(--color-text);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 1px;
  }
}
</style>
