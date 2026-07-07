<script lang="ts" setup>
import { NDynamicTags } from 'naive-ui';

defineProps<{
  modelValue: string[];
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: string[]): void;
}>();
</script>

<template>
  <div class="advanced-row advanced-row--tags">
    <label class="advanced-label">{{ $t('homepage.rule.filter') }}</label>
    <div class="advanced-control filter-tags">
      <NDynamicTags
        :value="modelValue"
        size="small"
        @update:value="emit('update:modelValue', $event)"
      />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.advanced-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 32px;

  &--tags {
    align-items: flex-start;
  }
}

.advanced-label {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  line-height: 32px;
}

.advanced-control {
  display: flex;
  justify-content: flex-end;

  :deep(.n-dynamic-tags) {
    justify-content: flex-end;
    min-height: 32px;

    .n-tag {
      height: 28px;
      margin: 2px 0 2px 6px !important;
    }

    .n-button {
      height: 28px;
    }
  }
}
</style>
