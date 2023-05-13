<script lang="ts" setup>
const props = withDefaults(
  defineProps<{
    running: boolean;
  }>(),
  {
    running: false,
  }
);
</script>

<template>
  <div wh-24px f-cer>
    <div rounded="1/2" f-cer border="2px solid white" wh-22px>
      <div
        :class="[running ? 'bg-running' : 'bg-stopped']"
        rounded="1/2"
        wh-10px
        transition-colors
      ></div>
    </div>
  </div>
</template>
