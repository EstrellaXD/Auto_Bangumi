<script lang="ts" setup>
definePage({
  name: 'Config',
});

const { getConfig, setConfig } = useConfigStore();
const { isMobile, isMobileOrTablet } = useBreakpointQuery();

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
        <config-passkey></config-passkey>
      </div>
    </div>

    <div class="config-actions">
      <ab-button
        :class="[{ 'flex-1': isMobileOrTablet }]"
        type="warn"
        @click="getConfig"
      >
        {{ $t('config.cancel') }}
      </ab-button>
      <ab-button
        :class="[{ 'flex-1': isMobileOrTablet }]"
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
  gap: 12px;
  margin-bottom: auto;

  @include forDesktop {
    grid-template-columns: 1fr 1fr;
  }
}

.config-col {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.config-actions {
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
  padding: 12px 0;
  backdrop-filter: blur(8px);
  background: color-mix(in srgb, var(--color-bg) 80%, transparent);
  @include safeAreaBottom(padding-bottom, 12px);
}
</style>
