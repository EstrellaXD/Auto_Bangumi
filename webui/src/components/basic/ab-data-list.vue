<script lang="ts" setup>
import { ref, computed } from 'vue';

export interface DataListColumn {
  key: string;
  title: string;
  render?: (row: Record<string, unknown>) => string;
  hidden?: boolean;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type DataItem = Record<string, any>;

const props = withDefaults(
  defineProps<{
    items: DataItem[];
    columns: DataListColumn[];
    selectable?: boolean;
    keyField?: string;
  }>(),
  {
    selectable: false,
    keyField: 'id',
  }
);

const emit = defineEmits<{
  (e: 'select', keys: unknown[]): void;
  (e: 'action', action: string, item: DataItem): void;
  (e: 'item-click', item: DataItem): void;
}>();

const selectedKeys = ref<Set<unknown>>(new Set());

const visibleColumns = computed(() =>
  props.columns.filter((col) => !col.hidden)
);

function toggleSelect(key: unknown) {
  if (selectedKeys.value.has(key)) {
    selectedKeys.value.delete(key);
  } else {
    selectedKeys.value.add(key);
  }
  emit('select', Array.from(selectedKeys.value));
}

function toggleSelectAll() {
  if (selectedKeys.value.size === props.items.length) {
    selectedKeys.value.clear();
  } else {
    props.items.forEach((item) => selectedKeys.value.add(item[props.keyField]));
  }
  emit('select', Array.from(selectedKeys.value));
}

function getCellValue(item: DataItem, column: DataListColumn): string {
  if (column.render) {
    return column.render(item);
  }
  return item[column.key] ?? '';
}

defineExpose({ selectedKeys, toggleSelectAll });
</script>

<template>
  <div class="ab-data-list">
    <!-- Select all header (when selectable) -->
    <div v-if="selectable && items.length > 0" class="ab-data-list__header">
      <label class="ab-data-list__select-all">
        <input
          type="checkbox"
          :checked="selectedKeys.size === items.length && items.length > 0"
          :indeterminate="selectedKeys.size > 0 && selectedKeys.size < items.length"
          @change="toggleSelectAll"
        />
        <span>{{ $t('common.selectAll') || 'Select All' }}</span>
      </label>
      <span class="ab-data-list__count">{{ items.length }} items</span>
    </div>

    <!-- Items -->
    <div
      v-for="item in items"
      :key="item[keyField]"
      class="ab-data-list__item"
      @click="emit('item-click', item)"
    >
      <!-- Checkbox -->
      <div v-if="selectable" class="ab-data-list__checkbox" @click.stop>
        <input
          type="checkbox"
          :checked="selectedKeys.has(item[keyField])"
          @change="toggleSelect(item[keyField])"
        />
      </div>

      <!-- Card content -->
      <div class="ab-data-list__card">
        <slot name="item" :item="item" :columns="visibleColumns">
          <!-- Default: key-value pairs -->
          <div
            v-for="col in visibleColumns"
            :key="col.key"
            class="ab-data-list__field"
          >
            <span class="ab-data-list__label">{{ col.title }}</span>
            <span class="ab-data-list__value">{{ getCellValue(item, col) }}</span>
          </div>
        </slot>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="items.length === 0" class="ab-data-list__empty">
      <slot name="empty">
        <span>No data</span>
      </slot>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.ab-data-list {
  display: flex;
  flex-direction: column;
  gap: 8px;

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
  }

  &__select-all {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: var(--color-text-secondary);
    cursor: pointer;

    input {
      width: 18px;
      height: 18px;
      accent-color: var(--color-primary);
    }
  }

  &__count {
    font-size: 12px;
    color: var(--color-text-muted);
  }

  &__item {
    display: flex;
    align-items: stretch;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    overflow: hidden;
    cursor: pointer;
    transition: border-color var(--transition-fast), box-shadow var(--transition-fast);

    &:active {
      border-color: var(--color-primary);
      box-shadow: var(--shadow-sm);
    }
  }

  &__checkbox {
    display: flex;
    align-items: center;
    padding: 12px;
    border-right: 1px solid var(--color-border);

    input {
      width: 18px;
      height: 18px;
      accent-color: var(--color-primary);
    }
  }

  &__card {
    flex: 1;
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 0;
  }

  &__field {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
  }

  &__label {
    font-size: 12px;
    color: var(--color-text-muted);
    flex-shrink: 0;
  }

  &__value {
    font-size: 14px;
    color: var(--color-text);
    text-align: right;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__empty {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 48px 16px;
    color: var(--color-text-muted);
    font-size: 14px;
  }
}
</style>
