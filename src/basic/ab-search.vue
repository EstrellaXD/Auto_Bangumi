<script lang="ts" setup>
import { Search } from '@icon-park/vue-next';

const props = withDefaults(
  defineProps<{
    value?: string;
  }>(),
  {
    value: '',
  }
);

const emit = defineEmits(['update:value', 'click-search']);

const onInput = (e: Event) => {
  const input = e.target as HTMLInputElement;
  emit('update:value', input.value);
};

const onSearch = () => {
  emit('click-search', props.value);
};
</script>

<template>
  <div
    bg="#7752B4"
    fx-cer
    rounded-12px
    h-36px
    px-12px
    space-x-12px
    w-276px
    focus-within:w-396px
    transition-width
  >
    <search
      theme="outline"
      size="24"
      fill="#fff"
      @click="onSearch"
      is-btn
      btn-click
    />

    <input
      type="text"
      :value="value"
      @input="onInput"
      @keyup.enter="onSearch"
      input-reset
    />
  </div>
</template>
