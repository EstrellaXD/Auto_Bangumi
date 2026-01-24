<script lang="ts" setup>
const { t } = useMyI18n();
const setupStore = useSetupStore();
const { accountData, downloaderData, rssData, mediaData, notificationData, isLoading } =
  storeToRefs(setupStore);
const router = useRouter();
const message = useMessage();

async function completeSetup() {
  isLoading.value = true;
  try {
    const request = setupStore.buildCompleteRequest();
    await apiSetup.complete(request);
    message.success(t('setup.review.success'));
    setupStore.$reset();
    router.push({ name: 'Login' });
  } catch (e) {
    message.error(t('setup.review.failed'));
  } finally {
    isLoading.value = false;
  }
}

function maskPassword(pwd: string): string {
  if (pwd.length <= 2) return '**';
  return pwd[0] + '*'.repeat(pwd.length - 2) + pwd[pwd.length - 1];
}
</script>

<template>
  <ab-container :title="t('setup.review.title')" class="wizard-step">
    <div class="step-content">
      <p class="step-subtitle">{{ t('setup.review.subtitle') }}</p>

      <div class="review-sections">
        <div class="review-section">
          <h4>{{ t('setup.account.title') }}</h4>
          <div class="review-item">
            <span class="review-label">{{ t('setup.account.username') }}</span>
            <span class="review-value">{{ accountData.username }}</span>
          </div>
          <div class="review-item">
            <span class="review-label">{{ t('setup.account.password') }}</span>
            <span class="review-value">{{ maskPassword(accountData.password) }}</span>
          </div>
        </div>

        <div class="review-section">
          <h4>{{ t('setup.downloader.title') }}</h4>
          <div class="review-item">
            <span class="review-label">{{ t('config.downloader_set.host') }}</span>
            <span class="review-value">{{ downloaderData.host }}</span>
          </div>
          <div class="review-item">
            <span class="review-label">{{ t('config.downloader_set.username') }}</span>
            <span class="review-value">{{ downloaderData.username }}</span>
          </div>
        </div>

        <div class="review-section">
          <h4>{{ t('setup.media.title') }}</h4>
          <div class="review-item">
            <span class="review-label">{{ t('setup.media.path') }}</span>
            <span class="review-value">{{ mediaData.path }}</span>
          </div>
        </div>

        <div v-if="!rssData.skipped && rssData.url" class="review-section">
          <h4>{{ t('setup.rss.title') }}</h4>
          <div class="review-item">
            <span class="review-label">{{ t('setup.rss.feed_name') }}</span>
            <span class="review-value">{{ rssData.name || rssData.url }}</span>
          </div>
        </div>

        <div v-if="!notificationData.skipped && notificationData.token" class="review-section">
          <h4>{{ t('setup.notification.title') }}</h4>
          <div class="review-item">
            <span class="review-label">{{ t('config.notification_set.type') }}</span>
            <span class="review-value">{{ notificationData.type }}</span>
          </div>
        </div>
      </div>

      <div class="wizard-actions">
        <ab-button size="small" type="secondary" @click="setupStore.prevStep()">
          {{ t('setup.nav.previous') }}
        </ab-button>
        <ab-button size="small" :disabled="isLoading" @click="completeSetup">
          {{ isLoading ? t('setup.review.completing') : t('setup.review.complete') }}
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

.review-sections {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.review-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 12px;

  h4 {
    margin: 0 0 8px;
    font-size: 12px;
    font-weight: 600;
    color: var(--color-text);
  }
}

.review-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 12px;

  &:not(:last-child) {
    border-bottom: 1px solid var(--color-border);
  }
}

.review-label {
  color: var(--color-text-muted);
}

.review-value {
  color: var(--color-text);
  font-family: monospace;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wizard-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}
</style>
