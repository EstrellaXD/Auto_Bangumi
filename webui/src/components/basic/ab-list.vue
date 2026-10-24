<script lang="ts" setup>
import { computed } from 'vue';
import AbSkeleton from './ab-skeleton.vue';
import AbEmpty from './ab-empty.vue';

type ListItem = Record<string, any>;

// Soft Ink 列表（取代 ab-data-list）：surface-2 填充行、悬停/聚焦态、
// 受控选择、加载骨架、i18n 空状态；density 供桌面数据页用紧凑行。
const {
  items,
  keyField = 'id',
  selectable = false,
  loading = false,
  density = 'comfortable',
} = defineProps<{
  items: ListItem[];
  keyField?: string;
  selectable?: boolean;
  loading?: boolean;
  density?: 'comfortable' | 'compact';
}>();

const emit = defineEmits<{
  'row-click': [item: ListItem];
}>();

/** 受控选择：v-model:selected */
const selected = defineModel<unknown[]>('selected', { default: () => [] });

const selectedSet = computed(() => new Set(selected.value));

const allSelected = computed(
  () => items.length > 0 && selectedSet.value.size === items.length
);

const someSelected = computed(
  () => selectedSet.value.size > 0 && !allSelected.value
);

function toggle(key: unknown) {
  const next = new Set(selectedSet.value);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  selected.value = Array.from(next);
}

function toggleAll() {
  selected.value = allSelected.value
    ? []
    : items.map((item) => item[keyField]);
}
</script>

<template>
  <div class="ab-list" :class="`ab-list--${density}`">
    <!-- 全选头（可选择时） -->
    <div v-if="selectable && items.length > 0" class="ab-list-header">
      <label class="ab-list-selectall">
        <input
          type="checkbox"
          :checked="allSelected"
          :indeterminate="someSelected"
          @change="toggleAll"
        >
        <span>{{ $t('common.selectAll') }}</span>
      </label>
      <span class="ab-list-count">{{ items.length }} {{ $t('common.items') }}</span>
    </div>

    <!-- 加载骨架 -->
    <AbSkeleton v-if="loading" preset="row" :count="3" />

    <!-- 行 -->
    <template v-else>
      <div
        v-for="item in items"
        :key="item[keyField]"
        class="ab-list-row"
        tabindex="0"
        @click="emit('row-click', item)"
        @keydown.enter="emit('row-click', item)"
      >
        <label
          v-if="selectable"
          class="ab-list-check"
          @click.stop
          @keydown.enter.stop
        >
          <input
            type="checkbox"
            :checked="selectedSet.has(item[keyField])"
            :aria-label="$t('common.select')"
            @change="toggle(item[keyField])"
          >
        </label>

        <div class="ab-list-row-content">
          <slot name="row" :item="item">
            {{ item[keyField] }}
          </slot>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="items.length === 0" class="ab-list-empty">
        <slot name="empty">
          <AbEmpty :title="$t('common.empty')" />
        </slot>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.ab-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.ab-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px;
}

.ab-list-selectall {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.ab-list-count {
  font-size: 12px;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  color: var(--color-text-muted);
}

.ab-list input[type='checkbox'] {
  width: 16px;
  height: 16px;
  accent-color: var(--color-primary);
  cursor: pointer;
}

.ab-list-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 14px;
  background: var(--color-surface-2);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background-color var(--transition-fast);

  // 触屏点按后不保留悬停态
  @media (hover: hover) {
    &:hover {
      background: var(--color-surface-hover);
    }
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 1px;
  }

  .ab-list--compact & {
    padding: 7px 12px;
    gap: 10px;
    border-radius: var(--radius-sm);
  }
}

.ab-list-check {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  cursor: pointer;
  // 扩大命中区
  padding: 6px;
  margin: -6px;
}

.ab-list-row-content {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.ab-list-empty {
  padding: 4px 0;
}
</style>
