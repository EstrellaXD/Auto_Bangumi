<script lang="ts" setup>
const { getConfig, setConfig } = useConfigStore();

getConfig();

definePage({
  name: 'Config',
});
</script>

<template>
  <div overflow-auto mt-12px flex-grow>
    <div h-full flex="~ col">
      <div grid="~ cols-2" gap-20px mb-auto>
        <div space-y-20px>
          <config-normal></config-normal>

          <config-parser></config-parser>

          <config-download></config-download>

          <config-manage></config-manage>
        </div>

        <div space-y-20px>
          <config-notification></config-notification>

          <config-proxy></config-proxy>

          <config-player></config-player>
        </div>
      </div>

      <div fx-cer justify-end gap-8px mt-20px>
        <ab-button type="warn" @click="getConfig">{{
          $t('config.cancel')
        }}</ab-button>
        <ab-button @click="setConfig">{{ $t('config.apply') }}</ab-button>
      </div>
    </div>
  </div>
</template>
