<script lang="ts" setup>
defineEmits(['click']);
</script>

<template>
  <button
    rounded="1/2"
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
$normal: #493475;
$hover: #756596;

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
  width: 6px;
  height: 18px;
  background: #fff;
}
</style>
