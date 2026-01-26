<script lang="ts" setup>
import { CloseSmall } from '@icon-park/vue-next';
import type { FilterOptions, SearchFilters } from '@/store/search';

const props = defineProps<{
  filters: SearchFilters;
  filterOptions: FilterOptions;
  filteredCount: number;
  totalCount: number;
}>();

const emit = defineEmits<{
  (e: 'toggle-filter', category: keyof SearchFilters, value: string): void;
  (e: 'clear-filters'): void;
}>();

const { t } = useMyI18n();

const categories = [
  { key: 'group' as const, label: () => t('search.filter.group') },
  { key: 'resolution' as const, label: () => t('search.filter.resolution') },
  { key: 'subtitleType' as const, label: () => t('search.filter.subtitle_type') },
  { key: 'season' as const, label: () => t('search.filter.season') },
];

const hasActiveFilters = computed(() => {
  return Object.values(props.filters).some((arr) => arr.length > 0);
});

function isActive(category: keyof SearchFilters, value: string): boolean {
  return props.filters[category].includes(value);
}

// Limit displayed chips, show "+N more" for overflow
const MAX_VISIBLE_CHIPS = 8;

function getVisibleOptions(options: string[]) {
  return options.slice(0, MAX_VISIBLE_CHIPS);
}

function getOverflowCount(options: string[]) {
  return Math.max(0, options.length - MAX_VISIBLE_CHIPS);
}
</script>

<template>
  <div v-if="Object.values(filterOptions).some(arr => arr.length > 0)" class="filters-section">
    <!-- Filter rows -->
    <div v-for="cat in categories" :key="cat.key" class="filter-row">
      <template v-if="filterOptions[cat.key].length > 0">
        <span class="filter-label">{{ cat.label() }}:</span>
        <div class="filter-chips">
          <button
            v-for="option in getVisibleOptions(filterOptions[cat.key])"
            :key="option"
            class="filter-chip"
            :class="{ active: isActive(cat.key, option) }"
            @click="emit('toggle-filter', cat.key, option)"
          >
            {{ option }}
          </button>
          <span
            v-if="getOverflowCount(filterOptions[cat.key]) > 0"
            class="filter-overflow"
          >
            +{{ getOverflowCount(filterOptions[cat.key]) }}
          </span>
        </div>
      </template>
    </div>

    <!-- Footer: Clear + Count -->
    <div class="filters-footer">
      <button
        v-if="hasActiveFilters"
        class="clear-btn"
        @click="emit('clear-filters')"
      >
        <CloseSmall :size="14" />
        {{ $t('search.filter.clear') }}
      </button>
      <span class="results-count">
        <template v-if="hasActiveFilters">
          {{ filteredCount }} / {{ totalCount }} {{ $t('search.filter.results') }}
        </template>
        <template v-else>
          {{ totalCount }} {{ $t('search.filter.results') }}
        </template>
      </span>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.filters-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
  transition: background-color var(--transition-normal), border-color var(--transition-normal);
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-secondary);
  min-width: 60px;
  flex-shrink: 0;
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.filter-chip {
  height: 28px;
  padding: 0 12px;
  font-size: 12px;
  font-family: inherit;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
  cursor: pointer;
  user-select: none;
  transition: all var(--transition-fast);

  &:hover:not(.active) {
    border-color: var(--color-primary);
    color: var(--color-primary);
  }

  &.active {
    background: var(--color-primary);
    border-color: var(--color-primary);
    color: #fff;
  }
}

.filter-overflow {
  font-size: 12px;
  color: var(--color-text-muted);
  padding: 0 8px;
}

.filters-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}

.clear-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  font-size: 12px;
  font-family: inherit;
  color: var(--color-danger);
  background: transparent;
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--color-danger);
    color: #fff;
  }
}

.results-count {
  font-size: 12px;
  color: var(--color-text-muted);
}
</style>
