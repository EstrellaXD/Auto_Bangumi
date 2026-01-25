<script lang="ts" setup>
import { Search } from '@icon-park/vue-next';
import { NSpin } from 'naive-ui';

withDefaults(
  defineProps<{
    provider: string;
    loading: boolean;
  }>(),
  {
    provider: '',
    loading: false,
  }
);

defineEmits<{ click: [] }>();
</script>

<template>
  <button
    class="search-trigger"
    role="search"
    aria-label="Open search"
    @click="$emit('click')"
  >
    <NSpin v-if="loading" :size="16" class="search-spinner" />
    <Search v-else theme="outline" size="18" class="search-icon" />

    <span class="search-placeholder">{{ $t('topbar.search.placeholder') }}</span>

    <span class="search-provider">{{ provider }}</span>
  </button>
</template>

<style lang="scss" scoped>
.search-trigger {
  display: flex;
  align-items: center;
  height: 36px;
  padding: 0 6px 0 12px;
  gap: 10px;
  min-width: 240px;
  border-radius: var(--radius-md);
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  cursor: pointer;
  font-family: inherit;
  transition: border-color var(--transition-fast),
              background-color var(--transition-normal),
              box-shadow var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
    background: var(--color-surface);
  }

  &:focus-visible {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 2px var(--color-primary-alpha);
  }

  @include forDesktop {
    min-width: 320px;
  }
}

.search-icon {
  flex-shrink: 0;
  color: var(--color-text-muted);
  transition: color var(--transition-fast);

  .search-trigger:hover & {
    color: var(--color-primary);
  }
}

.search-spinner {
  flex-shrink: 0;
}

.search-placeholder {
  flex: 1;
  text-align: left;
  font-size: 14px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-provider {
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  transition: background-color var(--transition-fast);

  .search-trigger:hover & {
    background: var(--color-primary-hover);
  }
}
</style>
