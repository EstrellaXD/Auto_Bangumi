<script lang="ts" setup>
definePage({
  name: 'Player',
});

const { url } = storeToRefs(usePlayerStore());
</script>

<template>
  <div class="page-embed">
    <div v-if="url === ''" class="empty-guide">
      <div class="empty-guide-header anim-fade-in">
        <div class="empty-guide-title">{{ $t('player.empty.title') }}</div>
        <div class="empty-guide-subtitle">{{ $t('player.empty.subtitle') }}</div>
      </div>

      <div class="empty-guide-steps">
        <div class="empty-guide-step anim-slide-up" style="--delay: 0.15s">
          <div class="empty-guide-step-number">1</div>
          <div class="empty-guide-step-content">
            <div class="empty-guide-step-title">{{ $t('player.empty.step1_title') }}</div>
            <div class="empty-guide-step-desc">{{ $t('player.empty.step1_desc') }}</div>
          </div>
        </div>

        <div class="empty-guide-step anim-slide-up" style="--delay: 0.3s">
          <div class="empty-guide-step-number">2</div>
          <div class="empty-guide-step-content">
            <div class="empty-guide-step-title">{{ $t('player.empty.step2_title') }}</div>
            <div class="empty-guide-step-desc">{{ $t('player.empty.step2_desc') }}</div>
          </div>
        </div>

        <div class="empty-guide-step anim-slide-up" style="--delay: 0.45s">
          <div class="empty-guide-step-number">3</div>
          <div class="empty-guide-step-content">
            <div class="empty-guide-step-title">{{ $t('player.empty.step3_title') }}</div>
            <div class="empty-guide-step-desc">{{ $t('player.empty.step3_desc') }}</div>
          </div>
        </div>
      </div>

      <RouterLink to="/config" class="empty-guide-action anim-slide-up" style="--delay: 0.6s">
        {{ $t('sidebar.config') }}
      </RouterLink>
    </div>

    <iframe
      v-else
      :src="url"
      frameborder="0"
      allowfullscreen="true"
      class="embed-frame"
    ></iframe>
  </div>
</template>

<style lang="scss" scoped>
.page-embed {
  overflow: auto;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}

.embed-frame {
  width: 100%;
  height: 100%;
  flex: 1;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.empty-guide {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 24px;
}

.empty-guide-header {
  text-align: center;
  margin-bottom: 32px;
}

.empty-guide-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 6px;
}

.empty-guide-subtitle {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.empty-guide-steps {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 400px;
  width: 100%;
}

.empty-guide-step {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 14px 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  transition: background-color var(--transition-normal),
              border-color var(--transition-normal);
}

.empty-guide-step-number {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-guide-step-content {
  flex: 1;
  min-width: 0;
}

.empty-guide-step-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 4px;
}

.empty-guide-step-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.empty-guide-action {
  margin-top: 24px;
  padding: 8px 24px;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: background-color var(--transition-fast);

  &:hover {
    background: var(--color-primary-hover);
  }
}

.anim-fade-in {
  animation: fadeIn 0.5s ease both;
}

.anim-slide-up {
  animation: slideUp 0.45s cubic-bezier(0.16, 1, 0.3, 1) both;
  animation-delay: var(--delay, 0s);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
