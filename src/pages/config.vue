<script lang="ts" setup>
const { getConfig } = useConfigStore();

onBeforeMount(() => getConfig());

definePage({
  name: 'Config',
});
</script>

<template>
  <div flex="~ wrap" gap-20px>
    <config-normal grow></config-normal>
    <config-parser grow></config-parser>
  </div>
</template>
