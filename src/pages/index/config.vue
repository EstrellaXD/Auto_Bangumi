<script lang="ts" setup>
const { getConfig, setConfig } = useConfigStore();

getConfig();

definePage({
  name: 'Config',
});
</script>

<template>
  <div gap-20px grid="~ cols-2">
    <config-normal></config-normal>

    <config-parser></config-parser>

    <config-download></config-download>

    <config-manage></config-manage>

    <config-notification></config-notification>

    <config-proxy></config-proxy>

    <div fx-cer justify-end gap-8px col-span-2>
      <ab-button type="warn" @click="getConfig">Cancel</ab-button>
      <ab-button @click="setConfig">Apply</ab-button>
    </div>
  </div>
</template>
