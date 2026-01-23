<script lang="ts" setup>
import { vOnClickOutside } from '@vueuse/components';
import type { BangumiRule } from '#/bangumi';

defineEmits<{
  (e: 'add-bangumi', bangumiRule: BangumiRule): void;
}>();

const showProvider = ref(false);
const { providers, provider, loading, inputValue, bangumiList } = storeToRefs(
  useSearchStore()
);
const { getProviders, onSearch, clearSearch } = useSearchStore();

onMounted(() => {
  getProviders();
});

function onSelect(site: string) {
  provider.value = site;
  showProvider.value = false;
}
</script>

<template>
  <ab-search
    v-model:inputValue="inputValue"
    :provider="provider"
    :loading="loading"
    @search="onSearch"
    @select="() => (showProvider = !showProvider)"
  />

  <transition name="dropdown">
    <div
      v-show="showProvider"
      v-on-click-outside="() => (showProvider = false)"
      class="provider-dropdown"
    >
      <div
        v-for="site in providers"
        :key="site"
        class="provider-item"
        @click="() => onSelect(site)"
      >
        {{ site }}
      </div>
    </div>
  </transition>

  <div v-on-click-outside="clearSearch" class="search-results">
    <transition-group name="fade-list" tag="ul" class="search-results-list">
      <li v-for="bangumi in bangumiList" :key="bangumi.order">
        <ab-bangumi-card
          :bangumi="bangumi.value"
          type="search"
          @click="() => $emit('add-bangumi', bangumi.value)"
        />
      </li>
    </transition-group>
  </div>
</template>

<style lang="scss" scoped>
.provider-dropdown {
  position: absolute;
  top: 84px;
  left: 540px;
  width: 120px;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-lg);
  z-index: 50;
  overflow: hidden;
  transition: background-color var(--transition-normal),
              border-color var(--transition-normal);
}

.provider-item {
  padding: 10px 12px;
  font-size: 14px;
  color: var(--color-primary);
  cursor: pointer;
  user-select: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: background-color var(--transition-fast), color var(--transition-fast);

  &:hover {
    background: var(--color-primary);
    color: #fff;
  }
}

.search-results {
  position: absolute;
  top: 84px;
  left: 192px;
  z-index: 30;
}

.search-results-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  list-style: none;
  padding: 0;
  margin: 0;
}
</style>
