<script lang="ts" setup>
withDefaults(
  defineProps<{
    running: boolean;
  }>(),
  {
    running: false,
  }
);
</script>

<template>
  <div wh-24 f-cer>
    <div rounded="1/2" f-cer border="2 solid white" wh-22>
      <div
        :class="[running ? 'bg-running' : 'bg-stopped']"
        rounded="1/2"
        wh-10
        transition-colors
      ></div>
    </div>
  </div>
</template>
