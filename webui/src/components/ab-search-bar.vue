<script lang="ts" setup>
import {ref} from 'vue';
import {vOnClickOutside} from "@vueuse/components";

const showProvider = ref(false);
const {providers, getProviders, provider, loading, onSearch} = useSearchStore();

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

</template>


<style lang="scss" scoped>

</style>