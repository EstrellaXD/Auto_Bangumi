<script lang="ts" setup>
import { Search } from '@icon-park/vue-next';

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

function onInput(e: Event) {
  const input = e.target as HTMLInputElement;
  emit('update:value', input.value);
}

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
    px-12px
    space-x-12px
    w-276px
    focus-within:w-396px
    transition-width
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
      @input="onInput"
      @keyup.enter="onSearch"
    />
  </div>
</template>
