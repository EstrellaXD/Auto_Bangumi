<script lang="ts" setup>
import { CircleCheck, Copy } from '@lucide/vue';

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
      <ab-icon-button
        class="copy-btn"
        :class="{ copied: props.copied }"
        :label="$t('common.copy')"
        @click="emit('copy')"
      >
        <CircleCheck v-if="props.copied" :size="14" />
        <Copy v-else :size="14" />
      </ab-icon-button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.rss-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.info-row {
  display: flex;
  align-items: center;
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

// 复制成功只换图标并着成功色（标记，不填充）
// 点击时指针仍悬停在按钮上（触屏 hover 会粘住），悬停态也保留成功色
.copy-btn.copied,
.copy-btn.copied:hover:not(:disabled) {
  color: var(--color-success);
}
</style>
