<script lang="ts" setup>
import { Down, Search } from '@icon-park/vue-next';
import { NSpin } from 'naive-ui';

withDefaults(
  defineProps<{
    providers: string[];
    loading: boolean;
  }>(),
  {
    loading: false,
  }
);

defineEmits(['search']);

const provider = defineModel<string>('provider');
const inputValue = defineModel<string>('inputValue');

const showProvider = ref(false);

function onSelect(site: string) {
  provider.value = site;
  showProvider.value = false;
}
</script>

<template>
  <div
    bg="#7752B4"
    text-white
    fx-cer
    rounded-12
    h-36
    pl-12
    gap-x-12
    w-400
    max-w-90vw
    shadow-inner
  >
    <Search
      v-if="!loading"
      theme="outline"
      size="24"
      fill="#fff"
      is-btn
      btn-click
      @click="$emit('search')"
    />
    <NSpin v-else :size="20" />

    <input
      v-model="inputValue"
      type="text"
      :placeholder="$t('topbar.search.placeholder')"
      input-reset
      @keyup.enter="$emit('search')"
    />

    <div rel w-100 h-full px-12 rounded-inherit class="provider" is-btn>
      <div
        fx-cer
        wh-full
        justify-between
        @click="() => (showProvider = !showProvider)"
      >
        <div text-h3 truncate>
          {{ provider }}
        </div>

        <Down />
      </div>

      <div
        v-show="showProvider"
        abs
        top="100%"
        left-0
        w-100
        rounded-12
        shadow
        bg-white
        z-1
        overflow-hidden
      >
        <div
          v-for="site in providers"
          :key="site"
          hover:bg-theme-row
          is-btn
          @click="() => onSelect(site)"
        >
          <div text="h3 primary" hover="text-white" p-12 truncate>
            {{ site }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.provider {
  background: #4e2a94;
}
</style>
