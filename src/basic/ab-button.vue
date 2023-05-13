<script lang="ts" setup>
const props = withDefaults(
  defineProps<{
    type?: 'primary' | 'warn';
    size?: 'big' | 'normal' | 'small';
  }>(),
  {
    type: 'primary',
    size: 'normal',
  }
);

defineEmits(['click']);
</script>

<template>
  <button
    text-white
    outline-none
    :class="[`type-${type}`, `size-${size}`]"
    @click="$emit('click')"
  >
    <slot></slot>
  </button>
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

.size {
  &-normal {
    border-radius: 6px;
    width: 171px;
    height: 36px;
  }

  &-big {
    font-size: 24px;
    border-radius: 10px;
    width: 276px;
    height: 55px;
  }

  &-small {
    font-size: 12px;
    border-radius: 6px;
    width: 86px;
    height: 28px;
  }
}
</style>
