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
      <div
        class="wizard-progress-bar"
        role="progressbar"
        :aria-label="
          t('setup.nav.step', {
            current: currentStep + 1,
            total: totalSteps,
          })
        "
        aria-valuemin="1"
        :aria-valuemax="totalSteps"
        :aria-valuenow="currentStep + 1"
      >
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

@media screen and (max-width: 639px) {
  .wizard-container {
    --setup-status-error: #b91c1c;
    --setup-status-success: #166534;

    width: 100%;
    max-width: none;
    min-width: 0;
    gap: 16px;
  }

  :global(.dark) .wizard-container {
    --setup-status-error: #fca5a5;
    --setup-status-success: #86efac;
  }

  .wizard-step-indicator {
    color: var(--color-text-secondary);
  }

  .wizard-content {
    min-width: 0;

    :deep(.wizard-step),
    :deep(.container-card),
    :deep(.container-body),
    :deep(.step-content),
    :deep(.welcome-content),
    :deep(.form-fields),
    :deep(.review-sections) {
      min-width: 0;
    }

    :deep(.setup-input),
    :deep(.setup-input-wide) {
      width: 100%;
      max-width: 100%;
      min-height: var(--touch-target);
      height: var(--touch-target);
      box-sizing: border-box;
      font-size: 16px;
      text-align: left;
    }

    :deep(.n-select),
    :deep(.type-select) {
      width: 100%;
      max-width: 100%;
      min-width: 0;
    }

    :deep(.wizard-actions .ab-btn),
    :deep(.test-section .ab-btn),
    :deep(.n-base-selection),
    :deep(.n-base-selection-label) {
      min-height: var(--touch-target);
    }

    :deep(.n-switch) {
      min-width: var(--touch-target);
      min-height: var(--touch-target);
    }

    :deep(.n-base-selection-label) {
      font-size: 16px;
    }

    :deep(.wizard-actions),
    :deep(.action-group),
    :deep(.test-section),
    :deep(.review-item) {
      min-width: 0;
      gap: 12px;
      flex-wrap: wrap;
    }

    :deep(.test-message) {
      min-width: 0;
      flex: 1 1 180px;
      overflow-wrap: anywhere;
    }

    :deep(.error-text),
    :deep(.test-message) {
      color: var(--setup-status-error);
      font-size: 12px;
      line-height: 1.4;
    }

    :deep(.test-message.success) {
      color: var(--setup-status-success);
    }

    :deep(.step-subtitle),
    :deep(.untested-hint),
    :deep(.review-label) {
      color: var(--color-text-secondary);
    }

    :deep(.welcome-subtitle),
    :deep(.welcome-description),
    :deep(.step-subtitle),
    :deep(.error-text),
    :deep(.untested-hint),
    :deep(.aria2-hint),
    :deep(.feed-info),
    :deep(.review-label),
    :deep(.review-value) {
      overflow-wrap: anywhere;
    }

    :deep(.review-label),
    :deep(.review-value) {
      min-width: 0;
    }

    :deep(.review-value) {
      max-width: 60%;
      overflow: visible;
      text-overflow: clip;
      white-space: normal;
      text-align: right;
    }
  }
}
</style>
