<script lang="ts" setup>
import { NSpin } from 'naive-ui';

const props = withDefaults(
  defineProps<{
    type?: 'primary' | 'warn';
    size?: 'big' | 'normal' | 'small';
    link?: string | null;
    loading?: boolean;
  }>(),
  {
    type: 'primary',
    size: 'normal',
    link: null,
    loading: false,
  }
);

defineEmits(['click']);

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
</script>

<template>
  <Component
    :is="link !== null ? 'a' : 'button'"
    :href="link"
    text-white
    outline-none
    f-cer
    :class="[`type-${type}`, buttonSize]"
    @click="$emit('click')"
  >
    <NSpin :show="loading" :size="loadingSize">
      <slot></slot>
    </NSpin>
  </Component>
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
</style>
