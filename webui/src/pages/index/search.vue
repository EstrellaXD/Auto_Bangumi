<script lang="ts" setup>
import { nextTick, onActivated, onDeactivated, ref } from 'vue';
import AbSearchPanel from '@/components/search/ab-search-panel.vue';
import { useSearchStore } from '@/store/search';

definePage({
  name: 'Search',
});

interface SearchPanelExpose {
  focusInput: () => void;
}

const searchPanel = ref<SearchPanelExpose | null>(null);
const { clearSelectedResult, closeSearch } = useSearchStore();

onActivated(() => {
  nextTick(() => searchPanel.value?.focusInput());
});

onDeactivated(() => {
  closeSearch();
  clearSelectedResult();
});
</script>

<template>
  <section class="search-page" :aria-label="$t('mobile.search_title')">
    <header class="search-page__header">
      <h1 id="search-page-title">{{ $t('mobile.search_title') }}</h1>
      <p>{{ $t('mobile.search_subtitle') }}</p>
    </header>

    <AbSearchPanel ref="searchPanel" class="search-page__panel" />
  </section>
</template>

<style lang="scss" scoped>
.search-page {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
}

.search-page__header {
  flex-shrink: 0;

  h1,
  p {
    margin: 0;
  }

  h1 {
    color: var(--color-text);
    font-size: 20px;
    line-height: 1.3;
  }

  p {
    margin-top: 2px;
    color: var(--color-text-secondary);
    font-size: 12px;
  }

  @include forTablet {
    display: none;
  }
}

.search-page__panel {
  flex: 1;
  min-height: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}
</style>
