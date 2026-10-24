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
      <!-- 过渡挂在不带 transition 的包裹层上：步骤根节点 .container-card 的
           scoped transition 会覆盖全局 .page-* 规则 -->
      <Transition name="page" mode="out-in">
        <div :key="currentStep">
          <wizard-step-welcome v-if="currentStep === 'welcome'" />
          <wizard-step-account v-else-if="currentStep === 'account'" />
          <wizard-step-downloader v-else-if="currentStep === 'downloader'" />
          <wizard-step-rss v-else-if="currentStep === 'rss'" />
          <wizard-step-notification
            v-else-if="currentStep === 'notification'"
          />
          <wizard-step-review v-else-if="currentStep === 'review'" />
        </div>
      </Transition>
    </wizard-container>
  </div>
</template>

<style lang="scss" scoped>
.page-setup {
  // 顶部对齐：步骤高度不同，居中会让进度条随步骤跳动；内容高于视口时可滚动
  min-height: 100dvh;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: clamp(24px, 12vh, 120px) 0 24px;
  background: var(--color-bg);
}
</style>
