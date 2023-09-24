<script lang="ts" setup>
import {ref} from 'vue';
import {vOnClickOutside} from "@vueuse/components";

defineEmits(['add-bangumi']);
const showProvider = ref(false);
const hasUpdate = ref(false);
const {
  providers,
  getProviders,
  provider,
  loading,
  onSearch,
  clearSearch,
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
      v-on-click-outside="clearSearch"
      abs top-84px left-192px z-8
  >
    <transition-group name="list" tag="ul" space-y-12px>
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
.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease;
}

.list-enter-from,
.list-leave-to {
  opacity: 0;
}

</style>