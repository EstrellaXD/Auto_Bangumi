<script lang="ts" setup>
// Soft Ink 行内提示：透明底 + 细线框，语义由加粗的彩色引导词承载 —
// 不用图标、不用彩色填充（拒绝 AI 模板味的着色警告框）。
withDefaults(
  defineProps<{
    type?: 'info' | 'warning' | 'danger';
    /** 加粗引导词，如 “Feed unreachable.”（语义色只落在这里） */
    title?: string;
    closable?: boolean;
  }>(),
  {
    type: 'info',
    title: '',
    closable: false,
  }
);

defineEmits<{ close: [] }>();
</script>

<template>
  <div
    class="ab-alert"
    :class="`ab-alert--${type}`"
    :role="type === 'info' ? 'status' : 'alert'"
  >
    <p class="ab-alert-text">
      <b v-if="title" class="ab-alert-title">{{ title }}</b>
      <slot></slot>
    </p>

    <span v-if="$slots.action" class="ab-alert-action">
      <slot name="action"></slot>
    </span>

    <button
      v-if="closable"
      type="button"
      class="ab-alert-close"
      :aria-label="$t('common.cancel')"
      @click="$emit('close')"
    >
      <svg viewBox="0 0 24 24" fill="none" width="11" height="11">
        <path
          d="M6 6l12 12M18 6 6 18"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
        />
      </svg>
    </button>
  </div>
</template>

<style lang="scss" scoped>
.ab-alert {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 13px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: transparent;
  font-size: 13px;
  color: var(--color-text);
}

.ab-alert-text {
  flex: 1;
  margin: 0;
  min-width: 0;
}

.ab-alert-title {
  font-weight: 650;
  margin-right: 4px;

  .ab-alert--info & {
    color: var(--color-primary);
  }

  .ab-alert--warning & {
    color: var(--color-warning);
  }

  .ab-alert--danger & {
    color: var(--color-danger);
  }
}

.ab-alert-action {
  flex-shrink: 0;
}

.ab-alert-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  margin: -2px -4px 0 0;
  padding: 0;
  border: none;
  border-radius: var(--radius-sm);
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
