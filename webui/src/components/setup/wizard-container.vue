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
        <!-- 按“已到第几步”计算，避免第一步进度条完全空白 -->
        <div
          class="wizard-progress-fill"
          :style="{ transform: `scaleX(${(currentStep + 1) / totalSteps})` }"
        />
      </div>
      <div class="wizard-step-indicator">
        {{
          t('setup.nav.step', { current: currentStep + 1, total: totalSteps })
        }}
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
  width: 100%;
  height: 100%;
  background: var(--color-primary);
  border-radius: 2px;
  transform-origin: left;
  transition: transform 0.3s ease-out;

  @media (prefers-reduced-motion: reduce) {
    transition: none;
  }
}

.wizard-step-indicator {
  font-size: 12px;
  color: var(--color-text-muted);
  text-align: right;
}

.wizard-content {
  display: flex;
  flex-direction: column;

  // On touch screens the compact desktop sizing (28px inputs/buttons) is
  // below the 44px touch-target minimum; widen and heighten the shared
  // wizard controls here instead of per step component.
  @include forTouch {
    :deep(.setup-input),
    :deep(.setup-input-wide) {
      width: 100%;
      height: var(--touch-target);
      font-size: 16px; // ≥16px stops iOS Safari from zooming the input
      text-align: left;
    }

    :deep(.wizard-actions .ab-btn),
    :deep(.test-section .ab-btn) {
      padding-left: 18px;
      padding-right: 18px;
    }
  }
}
</style>
