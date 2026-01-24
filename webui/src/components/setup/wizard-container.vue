<script lang="ts" setup>
defineProps<{
  currentStep: number;
  totalSteps: number;
}>();

const { t } = useMyI18n();
</script>

<template>
  <div class="wizard-container">
    <div class="wizard-progress">
      <div class="wizard-progress-bar">
        <div
          class="wizard-progress-fill"
          :style="{ width: `${(currentStep / (totalSteps - 1)) * 100}%` }"
        />
      </div>
      <div class="wizard-step-indicator">
        {{ t('setup.nav.step', { current: currentStep + 1, total: totalSteps }) }}
      </div>
    </div>

    <div class="wizard-content">
      <slot />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.wizard-container {
  width: 480px;
  max-width: 92%;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.wizard-progress {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.wizard-progress-bar {
  width: 100%;
  height: 4px;
  background: var(--color-border);
  border-radius: 2px;
  overflow: hidden;
}

.wizard-progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.wizard-step-indicator {
  font-size: 12px;
  color: var(--color-text-muted);
  text-align: right;
}

.wizard-content {
  display: flex;
  flex-direction: column;
}
</style>
