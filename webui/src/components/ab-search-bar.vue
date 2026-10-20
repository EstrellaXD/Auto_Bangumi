<script lang="ts" setup>
const { showModal, provider, loading } = storeToRefs(useSearchStore());
const { toggleModal, getProviders } = useSearchStore();

// 搜索弹窗首次打开时才加载
const { comp: SearchModal } = useLazyModal(
  showModal,
  () => import('./search/ab-search-modal.vue')
);

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
  <component :is="SearchModal" v-if="SearchModal" @close="toggleModal" />
</template>
