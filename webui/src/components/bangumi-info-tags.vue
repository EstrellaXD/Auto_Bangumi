<script lang="ts" setup>
import type { InfoTag } from '@/hooks/useBangumiRuleForm';

defineProps<{
  tags: InfoTag[];
}>();
</script>

<template>
  <div v-if="tags.length > 0" class="info-tags">
    <div
      v-for="tag in tags"
      :key="tag.type"
      class="info-tag"
      :class="`info-tag--${tag.type}`"
    >
      {{ tag.value }}
    </div>
  </div>
</template>

<style lang="scss" scoped>
.info-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.info-tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  border-radius: var(--radius-full);
  font-size: 13px;
  font-weight: 600;

  &--season {
    background: color-mix(in srgb, var(--color-primary) 12%, transparent);
    color: var(--color-primary);
  }

  &--resolution {
    background: color-mix(in srgb, var(--color-accent) 12%, transparent);
    color: var(--color-accent);
  }

  &--subtitle {
    background: color-mix(in srgb, var(--color-success) 12%, transparent);
    color: var(--color-success);
  }

  &--group {
    background: color-mix(in srgb, var(--color-warning) 12%, transparent);
    color: var(--color-warning);
  }
}
</style>
