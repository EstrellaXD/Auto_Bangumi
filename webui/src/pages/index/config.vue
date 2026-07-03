<script lang="ts" setup>
import { NButton } from 'naive-ui';

definePage({
  name: 'Config',
});

const { getConfig, setConfig } = useConfigStore();
const { isMobileOrTablet } = useBreakpointQuery();

const isSaving = ref(false);
const isResetting = ref(false);
const saveFailed = ref(false);

async function handleSave() {
  isSaving.value = true;
  try {
    const result = await setConfig();
    saveFailed.value = !result.ok;
  } finally {
    isSaving.value = false;
  }
}

async function handleReset() {
  isResetting.value = true;
  try {
    await getConfig();
    saveFailed.value = false;
  } finally {
    isResetting.value = false;
  }
}

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
        <config-search-provider></config-search-provider>
        <config-player></config-player>
        <config-llm></config-llm>
        <config-passkey></config-passkey>
        <config-security></config-security>
      </div>
    </div>

    <div class="config-actions">
      <NButton
        :size="isMobileOrTablet ? 'large' : 'medium'"
        :class="[{ 'flex-1': isMobileOrTablet }]"
        type="primary"
        secondary
        :loading="isResetting"
        :disabled="isResetting || isSaving"
        @click="handleReset"
      >
        {{ $t('config.cancel') }}
      </NButton>
      <NButton
        :size="isMobileOrTablet ? 'large' : 'medium'"
        :class="[{ 'flex-1': isMobileOrTablet }]"
        :type="saveFailed ? 'error' : 'primary'"
        :loading="isSaving"
        :disabled="isResetting || isSaving"
        @click="handleSave"
      >
        {{ $t('config.apply') }}
      </NButton>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.page-config {
  overflow-x: hidden;
  overflow-y: auto;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}

.config-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  flex: 1;
  min-width: 0; // Allow grid to shrink below content size
  width: 100%;

  @include forDesktop {
    grid-template-columns: 1fr 1fr;
  }
}

.config-col {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0; // Allow column to shrink below content size
  width: 100%;
}

.config-actions {
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
  padding: 12px;
  border-radius: var(--radius-md);
  backdrop-filter: blur(12px);
  background: color-mix(in srgb, var(--color-surface) 90%, transparent);
  border: 1px solid var(--color-border);

  @include forTablet {
    justify-content: flex-end;
    padding: 12px 0;
    border-radius: 0;
    border: none;
    background: color-mix(in srgb, var(--color-bg) 80%, transparent);
  }
}
</style>
