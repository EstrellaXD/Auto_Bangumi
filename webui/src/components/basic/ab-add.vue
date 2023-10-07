<script lang="ts" setup>
const props = withDefaults(
  defineProps<{
    round?: boolean;
    type?: 'large' | 'medium' | 'small';
  }>(),
  {
    round: false,
    type: 'large',
  }
);

defineEmits(['click']);

const buttonSize = computed(() => {
  switch (props.type) {
    case 'large':
      return 'wh-36px';
    case 'medium':
      return 'wh-24px';
    case 'small':
      return 'wh-12px';
  }
});

const lineSize = computed(() => {
  switch (props.type) {
    case 'large':
      return 'w-18px h-4px';
    case 'medium':
      return 'w-3px h-12px';
    case 'small':
      return 'w-2px h-6px';
  }
});
</script>

<template>
  <button
    :rounded="round ? '1/2' : '8px'"
    f-cer
    rel
    transition-colors
    class="box"
    :class="[`type-${type}`, buttonSize]"
    @click="$emit('click')"
  >
    <div :class="[`type-${type}`, lineSize]" class="line" abs />
    <div :class="[`type-${type}`, lineSize]" class="line" abs rotate-90></div>
  </button>
</template>

<style lang="scss" scoped>
$normal: #4e3c94;
$hover: #281e52;
$active: #8e8a9c;

.box {
  background: $normal;

  &:hover {
    background: $hover;
  }

  &:active {
    background: $normal;
  }
}

.line {
  border-radius: 1px;
  background: #fff;
}
</style>
