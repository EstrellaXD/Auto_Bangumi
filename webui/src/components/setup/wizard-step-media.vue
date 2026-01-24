<script lang="ts" setup>
const { t } = useMyI18n();
const setupStore = useSetupStore();
const { mediaData } = storeToRefs(setupStore);
</script>

<template>
  <ab-container :title="t('setup.media.title')" class="wizard-step">
    <div class="step-content">
      <p class="step-subtitle">{{ t('setup.media.subtitle') }}</p>

      <div class="form-fields">
        <ab-label :label="t('setup.media.path')">
          <input
            v-model="mediaData.path"
            type="text"
            placeholder="/downloads/Bangumi"
            class="setup-input setup-input-wide"
          />
        </ab-label>
      </div>

      <p class="path-hint">{{ t('setup.media.path_hint') }}</p>

      <div class="wizard-actions">
        <ab-button size="small" type="secondary" @click="setupStore.prevStep()">
          {{ t('setup.nav.previous') }}
        </ab-button>
        <ab-button size="small" @click="setupStore.nextStep()">
          {{ t('setup.nav.next') }}
        </ab-button>
      </div>
    </div>
  </ab-container>
</template>

<style lang="scss" scoped>
.wizard-step {
  width: 100%;
}

.step-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.step-subtitle {
  font-size: 12px;
  color: var(--color-text-muted);
  margin: 0;
}

.form-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.setup-input {
  outline: none;
  min-width: 0;
  width: 200px;
  height: 28px;
  padding: 0 12px;
  font-size: 12px;
  text-align: right;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
  }

  &:focus {
    border-color: var(--color-primary);
    box-shadow: 0 0 0 2px rgba(108, 74, 182, 0.2);
  }
}

.setup-input-wide {
  width: 260px;
}

.path-hint {
  font-size: 11px;
  color: var(--color-text-muted);
  margin: 0;
}

.wizard-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}
</style>
