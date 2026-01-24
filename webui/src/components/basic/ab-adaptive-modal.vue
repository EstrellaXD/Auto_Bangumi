<script lang="ts" setup>
const props = withDefaults(
  defineProps<{
    title: string;
    maskClick?: boolean;
    css?: string;
    maxHeight?: string;
  }>(),
  {
    title: '',
    maskClick: true,
    css: '',
    maxHeight: '85dvh',
  }
);

const show = defineModel('show', { default: false });

const { isMobile } = useBreakpointQuery();
</script>

<template>
  <!-- Mobile: Bottom sheet -->
  <ab-bottom-sheet
    v-if="isMobile"
    :show="show"
    :title="title"
    :closeable="maskClick"
    :max-height="maxHeight"
    @update:show="show = $event"
  >
    <slot />
  </ab-bottom-sheet>

  <!-- Desktop/Tablet: Centered popup -->
  <ab-popup
    v-else
    v-model:show="show"
    :title="title"
    :mask-click="maskClick"
    :css="css"
  >
    <slot />
  </ab-popup>
</template>
