<script lang="ts" setup>
import AbSearchModal from './search/ab-search-modal.vue';

const { showModal, provider, loading } = storeToRefs(useSearchStore());
const { toggleModal, getProviders } = useSearchStore();

onMounted(() => {
  getProviders();
});
</script>

<template>
  <!-- Search trigger button -->
  <ab-search
    :provider="provider"
    :loading="loading"
    @click="toggleModal"
  />

  <!-- Search Modal -->
  <AbSearchModal @close="toggleModal" />
</template>
