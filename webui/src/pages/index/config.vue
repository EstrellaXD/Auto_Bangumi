<script lang="ts" setup>
definePage({
  name: 'Config',
});

const { getConfig, setConfig } = useConfigStore();
const { isMobile } = useBreakpointQuery();

onActivated(() => {
  getConfig();
});
</script>

<template>
  <div class="page-config">
    <div class="config-grid">
      <div class="config-col">
        <config-normal></config-normal>
        <config-parser></config-parser>
        <config-download></config-download>
        <config-manage></config-manage>
      </div>

      <div class="config-col">
        <config-notification></config-notification>
        <config-proxy></config-proxy>
        <config-player></config-player>
        <config-openai></config-openai>
      </div>
    </div>

    <div class="config-actions">
      <ab-button
        :class="[{ 'flex-1': isMobile }]"
        type="warn"
        @click="getConfig"
      >
        {{ $t('config.cancel') }}
      </ab-button>
      <ab-button
        :class="[{ 'flex-1': isMobile }]"
        type="primary"
        @click="setConfig"
      >
        {{ $t('config.apply') }}
      </ab-button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.page-config {
  overflow: auto;
  flex-grow: 1;
}

.config-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
  margin-bottom: auto;

  @media (min-width: 1024px) {
    grid-template-columns: 1fr 1fr;
  }
}

.config-col {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.config-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}
</style>
