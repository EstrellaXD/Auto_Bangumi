<script lang="ts" setup>
const props = withDefaults(
  defineProps<{
    type?: 'primary' | 'warn';
    size?: 'big' | 'normal' | 'small';
    link?: string | null;
  }>(),
  {
    type: 'primary',
    size: 'normal',
    link: null,
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
    <slot></slot>
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
