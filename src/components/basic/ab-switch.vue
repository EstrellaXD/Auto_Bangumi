<script lang="ts" setup>
import { Switch } from '@headlessui/vue';

const checked = defineModel<boolean>('checked', {
  default: false,
});
</script>

<template>
  <Switch v-model="checked" as="template">
    <div
      is-btn
      w-48px
      h-28px
      rounded-full
      rel
      flex="inline items-center"
      transition-colors
      duration-300
      p-3px
      shadow="~ inset"
      class="box"
      :class="{ checked }"
    >
      <div
        wh-22px
        rounded="1/2"
        transition-all
        duration-300
        class="slider"
        :class="{ checked, 'translate-x-20px': checked }"
      ></div>
    </div>
  </Switch>
</template>

<style lang="scss" scope>
$bg-unchecked: #929292;
$bg-checked: #e7e7e7;

$slider-unchecked: #ececef;
$slider-unchecked-hover: #dbd8ec;

$slider-checked: #1c1259;
$slider-checked-hover: #62589e;

.box {
  background: $bg-unchecked;

  &.checked {
    background: $bg-checked;
  }

  &:hover .slider {
    &:not(.checked) {
      background: $slider-unchecked-hover;
    }

    &.checked {
      background: $slider-checked-hover;
    }
  }
}

.slider {
  &:not(.checked) {
    background: $slider-unchecked;
  }

  &.checked {
    background: $slider-checked;
  }
}
</style>
