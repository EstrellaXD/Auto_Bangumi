<script lang="ts" setup>
const { t } = useMyI18n();
const setupStore = useSetupStore();
const { rssData, validation } = storeToRefs(setupStore);

const isTesting = ref(false);
const testMessage = ref('');
const testSuccess = ref(false);
const feedTitle = ref('');
const itemCount = ref(0);

async function testFeed() {
  if (!rssData.value.url) return;
  isTesting.value = true;
  testMessage.value = '';
  feedTitle.value = '';
  try {
    const result = await apiSetup.testRSS(rssData.value.url);
    testSuccess.value = result.success;
    const { returnUserLangText } = useMyI18n();
    testMessage.value = returnUserLangText({
      en: result.message_en,
      'zh-CN': result.message_zh,
    });
    if (result.success) {
      feedTitle.value = result.title || '';
      itemCount.value = result.item_count || 0;
      if (!rssData.value.name && result.title) {
        rssData.value.name = result.title;
      }
      validation.value.rssTested = true;
    }
  } catch {
    testSuccess.value = false;
    testMessage.value = t('setup.rss.test_failed');
  } finally {
    isTesting.value = false;
  }
}

function skipStep() {
  rssData.value.skipped = true;
  setupStore.nextStep();
}

function handleNext() {
  rssData.value.skipped = false;
  setupStore.nextStep();
}
</script>

<template>
  <ab-container :title="t('setup.rss.title')" class="wizard-step">
    <div class="step-content">
      <p class="step-subtitle">{{ t('setup.rss.subtitle') }}</p>

      <div class="form-fields">
        <ab-label :label="t('setup.rss.url')">
          <input
            v-model="rssData.url"
            type="text"
            placeholder="https://mikanani.me/RSS/..."
            class="setup-input setup-input-wide"
          />
        </ab-label>

        <ab-label v-if="rssData.name" :label="t('setup.rss.feed_name')">
          <input
            v-model="rssData.name"
            type="text"
            class="setup-input"
          />
        </ab-label>
      </div>

      <div class="test-section">
        <ab-button
          size="small"
          type="secondary"
          :disabled="!rssData.url || isTesting"
          @click="testFeed"
        >
          {{ isTesting ? t('setup.downloader.testing') : t('setup.rss.test') }}
        </ab-button>
        <p v-if="testMessage" class="test-message" :class="{ success: testSuccess }">
          {{ testMessage }}
        </p>
      </div>

      <div v-if="feedTitle" class="feed-info">
        <p><strong>{{ t('setup.rss.feed_title') }}:</strong> {{ feedTitle }}</p>
        <p><strong>{{ t('setup.rss.item_count') }}:</strong> {{ itemCount }}</p>
      </div>

      <div class="wizard-actions">
        <ab-button size="small" type="secondary" @click="setupStore.prevStep()">
          {{ t('setup.nav.previous') }}
        </ab-button>
        <div class="action-group">
          <ab-button size="small" type="secondary" @click="skipStep">
            {{ t('setup.nav.skip') }}
          </ab-button>
          <ab-button
            size="small"
            :disabled="!validation.rssTested"
            @click="handleNext"
          >
            {{ t('setup.nav.next') }}
          </ab-button>
        </div>
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

.form-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.setup-input {
  outline: none;
  min-width: 0;
  width: 200px;
  height: 28px;
  padding: 0 12px;
  font-size: 12px;
  text-align: right;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
  }

  &:focus {
    border-color: var(--color-primary);
    box-shadow: 0 0 0 2px rgba(108, 74, 182, 0.2);
  }
}

.setup-input-wide {
  width: 260px;
}

.test-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.test-message {
  font-size: 11px;
  color: var(--color-error, #e53935);
  margin: 0;

  &.success {
    color: var(--color-success, #43a047);
  }
}

.feed-info {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 12px;
  font-size: 12px;

  p {
    margin: 0 0 4px;
    &:last-child { margin: 0; }
  }
}

.wizard-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.action-group {
  display: flex;
  gap: 8px;
}
</style>
