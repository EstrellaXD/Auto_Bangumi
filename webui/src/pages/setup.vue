<script lang="ts" setup>
definePage({
  name: 'Setup',
});

const setupStore = useSetupStore();
const { currentStep, currentStepIndex, steps } = storeToRefs(setupStore);
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
      <wizard-step-media v-else-if="currentStep === 'media'" />
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
</style>
