<script lang="ts" setup>
const { t } = useMyI18n();
const setupStore = useSetupStore();
const { downloaderData, validation } = storeToRefs(setupStore);

const isTesting = ref(false);
const testMessage = ref('');
const testSuccess = ref(false);

async function testConnection() {
  isTesting.value = true;
  testMessage.value = '';
  try {
    const result = await apiSetup.testDownloader({
      type: downloaderData.value.type,
      host: downloaderData.value.host,
      username: downloaderData.value.username,
      password: downloaderData.value.password,
      ssl: downloaderData.value.ssl,
    });
    testSuccess.value = result.success;
    const { returnUserLangText } = useMyI18n();
    testMessage.value = returnUserLangText({
      en: result.message_en,
      'zh-CN': result.message_zh,
    });
    validation.value.downloaderTested = result.success;
  } catch {
    testSuccess.value = false;
    testMessage.value = t('setup.downloader.test_failed');
  } finally {
    isTesting.value = false;
  }
}

function handleNext() {
  setupStore.nextStep();
}

const canTest = computed(() => {
  return downloaderData.value.host && downloaderData.value.username && downloaderData.value.password;
});
</script>

<template>
  <ab-container :title="t('setup.downloader.title')" class="wizard-step">
    <div class="step-content">
      <p class="step-subtitle">{{ t('setup.downloader.subtitle') }}</p>

      <div class="form-fields">
        <ab-label :label="t('config.downloader_set.host')">
          <input
            v-model="downloaderData.host"
            type="text"
            placeholder="172.17.0.1:8080"
            class="setup-input"
          />
        </ab-label>

        <ab-label :label="t('config.downloader_set.username')">
          <input
            v-model="downloaderData.username"
            type="text"
            placeholder="admin"
            class="setup-input"
          />
        </ab-label>

        <ab-label :label="t('config.downloader_set.password')">
          <input
            v-model="downloaderData.password"
            type="password"
            class="setup-input"
          />
        </ab-label>

        <ab-label :label="t('config.downloader_set.path')">
          <input
            v-model="downloaderData.path"
            type="text"
            placeholder="/downloads/Bangumi"
            class="setup-input"
          />
        </ab-label>

        <ab-label :label="t('config.downloader_set.ssl')">
          <ab-switch v-model="downloaderData.ssl" />
        </ab-label>
      </div>

      <div class="test-section">
        <ab-button
          size="small"
          type="secondary"
          :disabled="!canTest || isTesting"
          @click="testConnection"
        >
          {{ isTesting ? t('setup.downloader.testing') : t('setup.downloader.test') }}
        </ab-button>
        <p v-if="testMessage" class="test-message" :class="{ success: testSuccess }">
          {{ testMessage }}
        </p>
      </div>

      <div class="wizard-actions">
        <ab-button size="small" type="secondary" @click="setupStore.prevStep()">
          {{ t('setup.nav.previous') }}
        </ab-button>
        <ab-button
          size="small"
          :disabled="!validation.downloaderTested"
          @click="handleNext"
        >
          {{ t('setup.nav.next') }}
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

.wizard-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}
</style>
