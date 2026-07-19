<script lang="ts" setup>
import { CheckOne, Copy, PreviewOpen } from '@icon-park/vue-next';

const props = defineProps<{
  link: string;
  copied: boolean;
  previewRuleFilter?: string[];
  alwaysVisible?: boolean;
}>();

const emit = defineEmits<{
  (e: 'copy'): void;
}>();

const showPreview = ref(false);
</script>

<template>
  <div v-if="props.link || props.alwaysVisible" class="rss-section">
    <div class="info-row">
      <span class="info-label">{{ $t('search.confirm.rss') }}:</span>
      <span class="info-value info-value--link">{{ props.link || '-' }}</span>
      <div class="info-actions">
        <ab-icon-button
          size="sm"
          class="action-btn copy-btn"
          :class="{ copied: props.copied }"
          :label="$t('common.copy')"
          @click="emit('copy')"
        >
          <CheckOne v-if="props.copied" theme="outline" size="14" />
          <Copy v-else theme="outline" size="14" />
        </ab-icon-button>
        <ab-icon-button
          v-if="props.previewRuleFilter"
          size="sm"
          class="action-btn preview-btn"
          :label="$t('search.confirm.preview_open')"
          :disabled="!props.link"
          @click="showPreview = true"
        >
          <PreviewOpen theme="outline" size="14" />
        </ab-icon-button>
      </div>
    </div>
  </div>

  <bangumi-rss-preview-dialog
    v-if="props.previewRuleFilter"
    v-model:show="showPreview"
    :rss-link="props.link"
    :rule-filter="props.previewRuleFilter"
  />
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

.info-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.action-btn {
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
}

.copy-btn {
  &.copied {
    background: var(--color-success);
    border-color: var(--color-success);
    color: #fff;
  }
}
</style>
