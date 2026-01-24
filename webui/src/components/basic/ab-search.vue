<script lang="ts" setup>
import { Down, Search } from '@icon-park/vue-next';
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

defineEmits<{ select: []; search: [] }>();

const inputValue = defineModel<string>('inputValue');
</script>

<template>
  <div class="search-input" role="search">
    <button
      v-if="!loading"
      class="search-icon-btn"
      aria-label="Search"
      @click="$emit('search')"
    >
      <Search theme="outline" size="20" class="search-icon" />
    </button>
    <NSpin v-else :size="18" />

    <input
      v-model="inputValue"
      type="text"
      :placeholder="$t('topbar.search.placeholder')"
      class="search-field"
      aria-label="Search anime"
      @keyup.enter="$emit('search')"
    />

    <button
      class="search-provider"
      aria-label="Select search provider"
      @click="$emit('select')"
    >
      <div class="search-provider-label">{{ provider }}</div>
      <Down :size="14" />
    </button>
  </div>
</template>

<style lang="scss" scoped>
.search-input {
  display: flex;
  align-items: center;
  height: 36px;
  padding-left: 12px;
  gap: 10px;
  width: 360px;
  border-radius: var(--radius-md);
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  overflow: hidden;
  transition: border-color var(--transition-fast),
              background-color var(--transition-normal);

  &:focus-within {
    border-color: var(--color-primary);
    background: var(--color-surface);
  }
}

.search-icon-btn {
  display: flex;
  align-items: center;
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
  flex-shrink: 0;
}

.search-icon {
  color: var(--color-text-muted);
  transition: color var(--transition-fast);

  .search-icon-btn:hover & {
    color: var(--color-primary);
  }
}

.search-field {
  flex: 1;
  min-width: 0;
  background: transparent;
  border: none;
  outline: none;
  font-size: 14px;
  color: var(--color-text);

  &::placeholder {
    color: var(--color-text-muted);
  }
}

.search-provider {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  height: 100%;
  padding: 0 12px;
  min-width: 80px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  cursor: pointer;
  user-select: none;
  font-size: 13px;
  font-family: inherit;
  transition: background-color var(--transition-fast);

  &:hover {
    background: var(--color-primary-hover);
  }
}

.search-provider-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
