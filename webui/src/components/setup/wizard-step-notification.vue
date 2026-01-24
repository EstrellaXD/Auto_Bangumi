<script lang="ts" setup>
const { t } = useMyI18n();
const setupStore = useSetupStore();
const { notificationData, validation } = storeToRefs(setupStore);

const isTesting = ref(false);
const testMessage = ref('');
const testSuccess = ref(false);

const notificationTypes = [
  { id: 0, label: 'Telegram', value: 'telegram' },
  { id: 1, label: 'Server Chan', value: 'server-chan' },
  { id: 2, label: 'Bark', value: 'bark' },
  { id: 3, label: 'WeChat Work', value: 'wecom' },
];

async function testNotification() {
  isTesting.value = true;
  testMessage.value = '';
  try {
    const result = await apiSetup.testNotification({
      type: notificationData.value.type,
      token: notificationData.value.token,
      chat_id: notificationData.value.chat_id,
    });
    testSuccess.value = result.success;
    const { returnUserLangText } = useMyI18n();
    testMessage.value = returnUserLangText({
      en: result.message_en,
      'zh-CN': result.message_zh,
    });
    validation.value.notificationTested = result.success;
  } catch {
    testSuccess.value = false;
    testMessage.value = t('setup.notification.test_failed');
  } finally {
    isTesting.value = false;
  }
}

function skipStep() {
  notificationData.value.skipped = true;
  setupStore.nextStep();
}

function handleNext() {
  notificationData.value.skipped = false;
  notificationData.value.enable = true;
  setupStore.nextStep();
}

const canTest = computed(() => {
  return notificationData.value.token;
});
</script>

<template>
  <ab-container :title="t('setup.notification.title')" class="wizard-step">
    <div class="step-content">
      <p class="step-subtitle">{{ t('setup.notification.subtitle') }}</p>

      <div class="form-fields">
        <ab-label :label="t('config.notification_set.type')">
          <ab-select
            v-model="notificationData.type"
            :items="notificationTypes"
          />
        </ab-label>

        <ab-label :label="t('config.notification_set.token')">
          <input
            v-model="notificationData.token"
            type="text"
            class="setup-input setup-input-wide"
          />
        </ab-label>

        <ab-label :label="t('config.notification_set.chat_id')">
          <input
            v-model="notificationData.chat_id"
            type="text"
            class="setup-input"
          />
        </ab-label>
      </div>

      <div class="test-section">
        <ab-button
          size="small"
          type="secondary"
          :disabled="!canTest || isTesting"
          @click="testNotification"
        >
          {{ isTesting ? t('setup.downloader.testing') : t('setup.notification.test') }}
        </ab-button>
        <p v-if="testMessage" class="test-message" :class="{ success: testSuccess }">
          {{ testMessage }}
        </p>
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
            :disabled="!validation.notificationTested"
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
