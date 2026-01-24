<script lang="ts" setup>
definePage({
  name: 'Bangumi List',
});

const { bangumi } = storeToRefs(useBangumiStore());
const { getAll, openEditPopup } = useBangumiStore();

const refreshing = ref(false);

async function onRefresh() {
  refreshing.value = true;
  try {
    await getAll();
  } finally {
    refreshing.value = false;
  }
}

onActivated(() => {
  getAll();
});
</script>

<template>
  <ab-pull-refresh :loading="refreshing" @refresh="onRefresh">
  <div class="page-bangumi">
    <!-- Empty state guide -->
    <div v-if="!bangumi || bangumi.length === 0" class="empty-guide">
      <div class="empty-guide-header anim-fade-in">
        <div class="empty-guide-title">{{ $t('homepage.empty.title') }}</div>
        <div class="empty-guide-subtitle">{{ $t('homepage.empty.subtitle') }}</div>
      </div>

      <div class="empty-guide-steps">
        <div class="empty-guide-step anim-slide-up" style="--delay: 0.15s">
          <div class="empty-guide-step-number">1</div>
          <div class="empty-guide-step-content">
            <div class="empty-guide-step-title">{{ $t('homepage.empty.step1_title') }}</div>
            <div class="empty-guide-step-desc">{{ $t('homepage.empty.step1_desc') }}</div>
          </div>
        </div>

        <div class="empty-guide-step anim-slide-up" style="--delay: 0.3s">
          <div class="empty-guide-step-number">2</div>
          <div class="empty-guide-step-content">
            <div class="empty-guide-step-title">{{ $t('homepage.empty.step2_title') }}</div>
            <div class="empty-guide-step-desc">{{ $t('homepage.empty.step2_desc') }}</div>
          </div>
        </div>

        <div class="empty-guide-step anim-slide-up" style="--delay: 0.45s">
          <div class="empty-guide-step-number">3</div>
          <div class="empty-guide-step-content">
            <div class="empty-guide-step-title">{{ $t('homepage.empty.step3_title') }}</div>
            <div class="empty-guide-step-desc">{{ $t('homepage.empty.step3_desc') }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bangumi grid -->
    <transition-group
      v-else
      name="bangumi"
      tag="div"
      class="bangumi-grid"
    >
      <ab-bangumi-card
        v-for="i in bangumi"
        :key="i.id"
        :class="[i.deleted && 'grayscale']"
        :bangumi="i"
        type="primary"
        @click="() => openEditPopup(i)"
      ></ab-bangumi-card>
    </transition-group>

  </div>
  </ab-pull-refresh>
</template>

<style lang="scss" scoped>
.page-bangumi {
  overflow: auto;
  flex-grow: 1;
}

.bangumi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;

  @include forTablet {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 16px;
  }

  @include forDesktop {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 20px;
  }
}

.empty-guide {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
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

<style>
.bangumi-enter-active,
.bangumi-leave-active {
  transition: opacity var(--transition-normal), transform var(--transition-normal);
}
.bangumi-enter-from,
.bangumi-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
