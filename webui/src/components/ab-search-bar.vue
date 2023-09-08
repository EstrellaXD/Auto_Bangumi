<script lang="ts" setup>
import {ref} from 'vue';
import {vOnClickOutside} from "@vueuse/components";

defineEmits(['add-bangumi']);
const showProvider = ref(false);
const {
  providers,
  getProviders,
  provider,
  loading,
  onSearch,
  inputValue,
  bangumiList,
} = useSearchStore();

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
      @select="() => showProvider = !showProvider"
  />
  <div
      v-show="showProvider"
      v-on-click-outside="() => showProvider = false"
      abs top-84px
      left-540px w-100px
      rounded-12px
      shadow
      bg-white
      z-99
      overflow-hidden
  >
    <div
        v-for="site in providers"
        :key="site"
        hover:bg-theme-row
        is-btn
        @click="() => onSelect(site)"
    >
      <div
          text-h3
          text-primary
          hover:text-white
          p-12px
          truncate
      >
        {{ site }}
      </div>
    </div>
  </div>
  <div
      abs top-84px left-192px space-y-12px z-8
  >
    <TransitionGroup name="search-result">
      <ab-bangumi-card
          v-for="bangumi in bangumiList"
          :key="bangumi.id"
          :bangumi="bangumi"
          type="search"
          @click="() => $emit('add-bangumi', bangumi)"
      />
    </TransitionGroup>

  </div>

</template>


<style lang="scss" scoped>
.search-result-enter-active, .search-result-leave-active {
  transition: all 0.3s;
}

</style>