<script lang="ts" setup>
import { useMediaQuery } from '@vueuse/core';
import { NTooltip } from 'naive-ui';

// NTooltip 的统一封装：延迟、触屏回退（点击触发）与样式只在这里定一次。
const { content = '', placement = 'top', delay = 400 } = defineProps<{
  content?: string;
  placement?:
    | 'top' |
    'bottom' |
    'left' |
    'right' |
    'top-start' |
    'top-end' |
    'bottom-start' |
    'bottom-end';
  delay?: number;
}>();

// 触屏无法悬停：改为点击触发
const isTouch = useMediaQuery('(hover: none) and (pointer: coarse)');
</script>

<template>
  <NTooltip
    :placement="placement"
    :delay="delay"
    :trigger="isTouch ? 'click' : 'hover'"
    :style="{ maxWidth: '360px', overflowWrap: 'anywhere' }"
  >
    <template #trigger>
      <slot />
    </template>
    <slot name="content">
      {{ content }}
    </slot>
  </NTooltip>
</template>
