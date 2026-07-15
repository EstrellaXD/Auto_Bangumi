<script lang="ts" setup>
definePage({
  name: 'Setup',
});

const setupStore = useSetupStore();
const { currentStep, currentStepIndex } = storeToRefs(setupStore);
const { steps } = setupStore;
</script>

<template>
  <div class="page-setup">
    <wizard-container
      :current-step="currentStepIndex"
      :total-steps="steps.length"
    >
      <wizard-step-welcome v-if="currentStep === 'welcome'" />
      <wizard-step-account v-else-if="currentStep === 'account'" />
      <wizard-step-downloader v-else-if="currentStep === 'downloader'" />
      <wizard-step-rss v-else-if="currentStep === 'rss'" />
      <wizard-step-notification v-else-if="currentStep === 'notification'" />
      <wizard-step-review v-else-if="currentStep === 'review'" />
    </wizard-container>
  </div>
</template>

<style lang="scss" scoped>
.page-setup {
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
}

@media screen and (max-width: 639px) {
  .page-setup {
    width: 100%;
    height: auto;
    min-height: 100vh;
    min-height: 100dvh;
    align-items: flex-start;
    overflow-x: hidden;
    overflow-y: auto;
    box-sizing: border-box;
    padding-top: calc(20px + env(safe-area-inset-top, 0px));
    padding-right: calc(16px + env(safe-area-inset-right, 0px));
    padding-bottom: calc(20px + env(safe-area-inset-bottom, 0px));
    padding-left: calc(16px + env(safe-area-inset-left, 0px));
  }
}
</style>
