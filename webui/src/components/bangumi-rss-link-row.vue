<script lang="ts" setup>
import { CheckOne, Copy } from '@icon-park/vue-next';

const props = defineProps<{
  link: string;
  copied: boolean;
}>();

const emit = defineEmits<{
  (e: 'copy'): void;
}>();
</script>

<template>
  <div v-if="props.link" class="rss-section">
    <div class="info-row">
      <span class="info-label">{{ $t('search.confirm.rss') }}:</span>
      <span class="info-value info-value--link">{{ props.link }}</span>
      <button
        class="copy-btn"
        :class="{ copied: props.copied }"
        @click="emit('copy')"
      >
        <CheckOne v-if="props.copied" theme="outline" size="14" />
        <Copy v-else theme="outline" size="14" />
      </button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.rss-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.info-label {
  flex-shrink: 0;
  width: 70px;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.info-value {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: var(--color-text);
  word-break: break-all;

  &--link {
    color: var(--color-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.copy-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--color-text-muted);
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
    color: var(--color-primary);
  }

  &.copied {
    background: var(--color-success);
    border-color: var(--color-success);
    color: #fff;
  }
}
</style>
