<script lang="ts" setup>
import AbSearchModal from './search/ab-search-modal.vue';

const searchStore = useSearchStore();
const { showModal, provider, loading } = storeToRefs(searchStore);
const { closeModal, openModal } = searchStore;
const triggerContainer = ref<HTMLElement | null>(null);

watch(showModal, (isOpen, wasOpen) => {
  if (isOpen || !wasOpen) return;
  triggerContainer.value?.querySelector<HTMLElement>('button')?.focus();
});

onBeforeUnmount(() => {
  if (showModal.value) closeModal();
});
</script>

<template>
  <!-- Search trigger button -->
  <div ref="triggerContainer" class="search-bar-trigger">
    <ab-search :provider="provider" :loading="loading" @click="openModal" />
  </div>

  <!-- Search Modal -->
  <AbSearchModal />
</template>

<style lang="scss" scoped>
.search-bar-trigger {
  width: 100%;
}
</style>
