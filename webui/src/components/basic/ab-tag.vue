<script lang="ts" setup>
// Soft Ink 标签：细线框 + 语义色方块标记，文字始终为墨色 —
// 颜色不承载文字（拒绝粉彩胶囊）。不截断 CJK 标题。
withDefaults(
  defineProps<{
    type?: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
    title?: string;
    closable?: boolean;
  }>(),
  {
    type: 'neutral',
    title: '',
    closable: false,
  }
);

defineEmits<{ close: [] }>();
</script>

<template>
  <span class="ab-tag" :class="`ab-tag--${type}`">
    <span class="ab-tag-text"
      ><slot>{{ title }}</slot></span
    >
    <button
      v-if="closable"
      type="button"
      class="ab-tag-close"
      :aria-label="$t('common.remove')"
      @click.stop="$emit('close')"
    >
      <svg viewBox="0 0 24 24" fill="none" width="10" height="10">
        <path
          d="M6 6l12 12M18 6 6 18"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
        />
      </svg>
    </button>
  </span>
</template>

<style lang="scss" scoped>
.ab-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  padding: 2px 8px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: transparent;
  color: var(--color-text);
  font-size: 12px;
  font-weight: 500;
  transition: border-color var(--transition-fast), color var(--transition-fast);

  // 语义色方块标记
  &::before {
    content: '';
    width: 7px;
    height: 7px;
    border-radius: 2px;
    flex-shrink: 0;
  }

  &--success::before {
    background: var(--color-success);
  }

  &--warning::before {
    background: var(--color-warning);
  }

  &--danger::before {
    background: var(--color-danger);
  }

  &--info::before {
    background: var(--color-primary);
  }

  &--neutral {
    color: var(--color-text-secondary);

    &::before {
      background: var(--color-text-muted);
    }
  }
}

.ab-tag-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ab-tag-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  padding: 2px;
  border: none;
  border-radius: 2px;
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
