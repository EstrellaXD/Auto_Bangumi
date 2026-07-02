<script lang="ts" setup>
import { NButton } from 'naive-ui';

const { t } = useMyI18n();
const setupStore = useSetupStore();
</script>

<template>
  <ab-container :title="t('setup.welcome.title')" class="wizard-step">
    <div class="welcome-content">
      <p class="welcome-subtitle">{{ t('setup.welcome.subtitle') }}</p>
      <p class="welcome-description">{{ t('setup.welcome.description') }}</p>

      <div class="wizard-actions">
        <div></div>
        <NButton type="primary" size="small" @click="setupStore.nextStep()">
          {{ t('setup.welcome.start') }}
        </NButton>
      </div>
    </div>
  </ab-container>
</template>

<style lang="scss" scoped>
.wizard-step {
  width: 100%;
}

.welcome-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.welcome-subtitle {
  font-size: 14px;
  color: var(--color-text);
  margin: 0;
}

.welcome-description {
  font-size: 13px;
  line-height: 1.6;
  // muted (#94A3B8) 在白底上不足 AA 对比度，正文用 secondary
  color: var(--color-text-secondary);
  margin: 0;
}

.wizard-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}
</style>
