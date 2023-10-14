<script lang="ts" setup xmlns="http://www.w3.org/1999/html">

import {NSpin} from 'naive-ui';
import {Down} from "@icon-park/vue-next";
import {computed} from "vue";

const props = withDefaults(
    defineProps<{
      type?: 'primary' | 'warn';
      size?: 'big' | 'normal' | 'small';
      link?: string | null;
      loading?: boolean;
      selections: string[];
    }>(),
    {
      type: 'primary',
      size: 'normal',
      link: null,
      loading: false,
    }
);

defineEmits(['click']);

const selected = ref<string>(
    props.selections[0]
);
const showSelections = ref<boolean>(false);


const buttonSize = computed(() => {
  switch (props.size) {
    case 'big':
      return 'rounded-10px text-h1 w-276px h-55px text-h1';
    case 'normal':
      return 'rounded-6px w-170px h-36px';
    case 'small':
      return 'rounded-6px w-86px h-28px text-main';
  }
});

const selectboxSize = computed(() => {
  switch (props.size) {
    case 'big':
      return 'w-276px rounded-10px text-h1';
    case 'normal':
      return 'w-170px rounded-6px';
    case 'small':
      return 'w-86px rounded-6px text-main';
  }
});

const loadingSize = computed(() => {
  switch (props.size) {
    case 'big':
      return 'large';
    case 'normal':
      return 'small';
    case 'small':
      return 18;
  }
});

function onSelect(selection: string) {
  selected.value = selection;
  showSelections.value = false;
  console.log(selected.value);
}

</script>

<template>
  <div
      :class="buttonSize"
      f-cer
      overflow-hidden
  >
    <Component
        :is="link !== null ? 'a' : 'button'"
        :href="link"
        text-white
        outline-none
        wh-full
        pl-12px
        :class="[`type-${type}`]"
        @click="$emit('click', selected)"
    >
      <NSpin :show="loading" :size="loadingSize">
        <div text-main>{{ selected }}</div>
      </NSpin>
    </Component>
    <div
        is-btn
        px-12px
        h-full
        f-cer
        :class="[`selector-${type}`]"
        @click="() => showSelections = !showSelections"
    >
      <Down fill="white"/>
    </div>
  </div>
  <div
      v-if="showSelections"
      abs
      z-70
      :class="selectboxSize"
      overflow-hidden
      class="select-box"
  >
    <div
        v-for="selection in selections"
        :key="selection"
        is-btn
        wh-full
        f-cer
        text-main
        py-8px
        text-white
        :class="[`type-${type}`]"
        @click="onSelect(selection)"
    >
      {{ selection }}
    </div>
  </div>
</template>

<style lang="scss" scoped>
.type {
  &-primary {
    @include bg-mouse-event(#4e3c94, #281e52, #8e8a9c);
  }

  &-warn {
    @include bg-mouse-event(#943c61, #521e2a, #9c8a93);
  }
}
.selector {
  &-primary {
    @include bg-mouse-event(#4e3c94, #281e52, #8e8a9c);
  }
  &-warn {
    @include bg-mouse-event(#943c61, #521e2a, #9c8a93);
  }
}

.select-box {
  transform: TranslateY(80%) TranslateX(-111%);
}
</style>