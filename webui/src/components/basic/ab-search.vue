<script lang="ts" setup>
import {Search} from '@icon-park/vue-next';
import {ref} from 'vue';
import {Down, Up} from '@icon-park/vue-next';
import {isString} from "lodash";
import type {SelectItem} from "#/components";
import {apiSearch} from "@/api/search";
import {
  Subject,
  tap,
  map,
  switchMap,
  debounceTime,
} from "rxjs";
import type {BangumiRule} from "#/bangumi";

const props = withDefaults(
    defineProps<{
      value?: string;
      provider: string[];
      placeholder?: string;
    }>(),
    {
      value: '',
      provider: ['Mikan', 'Dmhy', 'Nyaa'],
      placeholder: '',
    }
);

const emit = defineEmits(['update:value', 'click-search']);

const selected = ref<SelectItem | string>(
    (props.provider?.[0] ?? '')
);

const selectedProvider = computed(() => {
  if (isString(selected.value)) {
    return selected.value;
  } else {
    return selected.value.label ?? selected.value.value;
  }
});

const onSelect = ref(false);

const input$ = new Subject<string>();
const onInput = (value: string) => {
  input$.next(value);
};

const bangumiInfo$ = apiSearch.get('魔女之旅')

input$.pipe(
    debounceTime(500),
    tap((input: string) => {
      console.log(input);
    }),
    switchMap((input: string) => {
      return apiSearch.get(input, site);
    }),
    tap((bangumi: BangumiRule) => console.log(bangumi)),
    tap((bangumi: BangumiRule) => {
      console.log('bangumi', bangumi)
      // set bangumi info to Search Result List
    }),
).subscribe({
  complete() {

  }
});

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
        @keyup.enter="onSearch"
    />
    <div
        h-full
        f-cer
        justify-between
        px-12px
        w-100px
        is-btn
        @click="() => onSelect = !onSelect"
        class="provider-select"
    >
      <div text-h3>
        {{ selectedProvider }}
      </div>
      <div class="provider-select">
        <Down/>
      </div>
    </div>
  </div>
  <div v-show="onSelect" abs top-84px left-540px w-100px rounded-12px shadow bg-white z-99 overflow-hidden>
    <div
        v-for="i in provider"
        :key="i"
        hover:bg-theme-row
        is-btn
        @click="() => {
        selected = i;
        onSelect = false;
      }"

    >
      <div
          text-h3
          text-primary
          hover:text-white
          p-12px
      >
        {{ i }}
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>

.provider-select {
  background: #4E2A94;
}

</style>
