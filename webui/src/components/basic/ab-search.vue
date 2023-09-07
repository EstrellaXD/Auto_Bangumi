<script lang="ts" setup>
import {Down, Search} from '@icon-park/vue-next';

const {
  onSelect,
  onSearch,
  inputValue,
  selectingProvider,
  provider,
  providers,
  getProviders,
  bangumiList
} = useSearchStore();


onMounted(() => {
  getProviders();
});

</script>

<template>
  <div
      bg="#7752B4"
      text-white
      fx-cer
      rounded-12px
      h-36px
      pl-12px
      space-x-12px
      w-400px
      overflow-hidden
      shadow-inner
  >
    <Search
        theme="outline"
        size="24"
        fill="#fff"
        is-btn
        btn-click
        @click="onSearch"
    />

    <input
        v-model="inputValue"
        type="text"
        :placeholder="$t('topbar.search.placeholder')"
        input-reset
        @keyup.enter="onSearch"
    />
    <div
        h-full
        f-cer
        justify-between
        px-12px
        w-100px
        is-btn
        class="provider-select"
        @click="() => selectingProvider = !selectingProvider"
    >
      <div text-h3 truncate>
        {{ provider }}
      </div>
      <div class="provider-select">
        <Down/>
      </div>
    </div>
  </div>
  <div v-show="selectingProvider" abs top-84px left-540px w-100px rounded-12px shadow bg-white z-99 overflow-hidden>
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
      abs top-84px left-200px space-y-8px z-98
  >
    <ab-bangumi-card
        v-for="(item, index) in bangumiList"
        :key="index"
        :bangumi="item"
        type="search"
        transition-opacity
    />
  </div>
</template>

<style lang="scss" scoped>

.provider-select {
  background: #4E2A94;
}

.list-enter-active, .list-leave-active {
  transition: opacity 0.5s ease;
}

</style>
