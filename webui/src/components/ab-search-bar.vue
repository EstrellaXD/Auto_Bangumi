<script lang="ts" setup>
import AbSearchModal from './search/ab-search-modal.vue';
import type { BangumiRule } from '#/bangumi';

defineEmits<{
  (e: 'add-bangumi', bangumiRule: BangumiRule): void;
}>();

const { showModal, provider, loading, inputValue } = storeToRefs(useSearchStore());
const { toggleModal, onSearch, getProviders } = useSearchStore();

onMounted(() => {
  getProviders();
});

// Handle click on search input - toggle modal
function handleSearchClick() {
  toggleModal();
}

// Handle search trigger from input
function handleSearch() {
  if (!showModal.value) {
    toggleModal();
  }
  onSearch();
}
</script>

<template>
  <!-- Compact search trigger -->
  <ab-search
    v-model:input-value="inputValue"
    :provider="provider"
    :loading="loading"
    @search="handleSearch"
    @select="handleSearchClick"
    @click="handleSearchClick"
  />

  <!-- Search Modal -->
  <AbSearchModal
    @close="toggleModal"
    @add-bangumi="(bangumi) => $emit('add-bangumi', bangumi)"
  />
</template>
