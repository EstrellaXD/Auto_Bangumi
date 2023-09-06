<script lang="ts" setup>
import {Down, Search} from '@icon-park/vue-next';
import {ref} from 'vue';


const inputValue = ref<string>('');
const selectingProvider = ref<boolean>(false);

const {input$, provider, providers, getProviders, bangumiList} = useSearchStore();

/**
 * - 输入中 debounce 600ms 后触发搜索
 * - 按回车或点击搜索 icon 按钮后触发搜索
 * - 切换 provider 源站时触发搜索
 */


function onInput(e: Event) {
  const value = (e.target as HTMLInputElement).value;
  input$.next(value);
  inputValue.value = value;
}

function onSearch() {
  input$.next(inputValue.value);
}

function onSelect(site: string) {
  provider.value = site;
  selectingProvider.value = !selectingProvider.value
  onSearch();
}

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
      transition-width
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
        type="text"
        placeholder="Input to search"
        input-reset
        :value="inputValue"
        @keyup.enter="onSearch"
        @input="onInput"
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
        transition-all
    />
  </div>
</template>

<style lang="scss" scoped>

.provider-select {
  background: #4E2A94;
}

.fade-enter-active, .fade-leave-active {
  transition: opacity .3s;
}

</style>
