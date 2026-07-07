<script lang="ts" setup>
import { NTooltip } from 'naive-ui';

// NTooltip 的统一封装：延迟、触屏回退（点击触发）与样式只在这里定一次。
withDefaults(
  defineProps<{
    content?: string;
    placement?:
      | 'top'
      | 'bottom'
      | 'left'
      | 'right'
      | 'top-start'
      | 'top-end'
      | 'bottom-start'
      | 'bottom-end';
    delay?: number;
  }>(),
  {
    content: '',
    placement: 'top',
    delay: 400,
  }
);
</script>

<template>
  <NTooltip :placement="placement" :delay="delay" trigger="hover">
    <template #trigger>
      <slot />
    </template>
    <slot name="content">{{ content }}</slot>
  </NTooltip>
</template>
