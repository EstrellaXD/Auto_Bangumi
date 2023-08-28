<script lang="ts" setup>
withDefaults(
  defineProps<{
    round?: boolean;
  }>(),
  {
    round: false,
  }
);

defineEmits(['click']);

</script>

<template>
  <button
    :rounded="round ? '1/2' : '8px'"
    wh-36px
    f-cer
    rel
    transition-colors
    class="box"
    @click="$emit('click')"
  >
    <div class="line" abs></div>
    <div class="line" abs rotate-90></div>
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
  width: 4px;
  height: 18px;
  border-radius: 1px;
  background: #fff;
}
</style>
