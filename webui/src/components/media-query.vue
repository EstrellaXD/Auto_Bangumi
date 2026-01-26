<script lang="ts" setup>
const { isMobile, isTablet } = useBreakpointQuery();
</script>

<template>
  <template v-if="isMobile">
    <slot name="mobile"></slot>
  </template>

  <template v-else-if="isTablet">
    <slot name="tablet">
      <!-- Fallback: if no tablet slot provided, use mobile -->
      <slot name="mobile"></slot>
    </slot>
  </template>

  <template v-else>
    <slot></slot>
  </template>
</template>

<style lang="scss" scoped></style>
