<script lang="ts" setup>
import {Down, Search} from '@icon-park/vue-next';
import {ref} from 'vue';

const props = withDefaults(
    defineProps<{
      value?: string;
      placeholder?: string;
    }>(),
    {
      value: '',
      placeholder: '',
    }
);

const emit = defineEmits(['update:value', 'click-search']);
const { site, providers, bangumiInfo$} = storeToRefs(useSearchStore());
const { getProviders, onInput } = useSearchStore();

onMounted(() => {
  getProviders();
});

const selectedProvider = computed(() => {
  return site.value || '';
});

const onSelect = ref(false);

function onSearch() {
  emit('click-search', props.value);
}
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
        :value="value"
        :placeholder="placeholder"
        input-reset
        @keyup.enter="onInput"
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
        @click="() => onSelect = !onSelect"
    >
      <div text-h3 truncate>
        {{ selectedProvider }}
      </div>
      <div class="provider-select">
        <Down/>
      </div>
    </div>
  </div>
  <div v-show="onSelect" abs top-84px left-540px w-100px rounded-12px shadow bg-white z-99 overflow-hidden>
    <div
        v-for="i in providers"
        :key="i"
        hover:bg-theme-row
        is-btn
        @click="() => {
        site = i;
        onSelect = false;
      }"

    >
      <div
          text-h3
          text-primary
          hover:text-white
          p-12px
          truncate
      >
        {{ i }}
      </div>
    </div>
  </div>
  <div abs top-84px left-200px z-98>
    <ab-bangumi-card
        name="name"
        season=1
        poster=""
        group="Lilith-Raws"
        type="search"
    />
  </div>
</template>

<style lang="scss" scoped>

.provider-select {
  background: #4E2A94;
}

</style>
