<script lang="ts" setup>
import { NSwitch } from 'naive-ui';

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

// A passed test only vouches for the values it ran against — editing any
// connection field re-arms the untested state.
watch(
  () => [
    downloaderData.value.type,
    downloaderData.value.host,
    downloaderData.value.username,
    downloaderData.value.password,
    downloaderData.value.ssl,
  ],
  () => {
    validation.value.downloaderTested = false;
    testSuccess.value = false;
    testMessage.value = '';
  }
);

const downloaderTypeOptions = [
  { label: 'qBittorrent', value: 'qbittorrent' },
  { label: 'aria2', value: 'aria2' },
];

// Password intentionally not required — qB with bypass_local_auth has none.
// aria2 authenticates via RPC secret (password field); it has no username.
const canTest = computed(() => {
  return (
    downloaderData.value.host &&
    (downloaderData.value.type === 'aria2' || downloaderData.value.username)
  );
});

// The connection test is encouraged but must not be a dead end: a backend
// that can't reach qB right now (network, container DNS) would otherwise
// trap the user in the wizard with no way forward.
const canProceed = computed(() => Boolean(downloaderData.value.host));
</script>

<template>
  <ab-container :title="t('setup.downloader.title')" class="wizard-step">
    <div class="step-content">
      <p class="step-subtitle">
        {{ t('setup.downloader.subtitle') }}
      </p>

      <div class="form-fields">
        <ab-field :label="t('config.downloader_set.type')">
          <ab-select
            v-model="downloaderData.type"
            :options="downloaderTypeOptions"
            :aria-label="t('config.downloader_set.type')"
          />
        </ab-field>

        <p v-if="downloaderData.type === 'aria2'" class="aria2-hint">
          {{ t('config.downloader_set.aria2_hint') }}
        </p>

        <ab-field :label="t('config.downloader_set.host')">
          <ab-input
            v-model="downloaderData.host"
            :aria-label="t('config.downloader_set.host')"
            placeholder="172.17.0.1:8080"
          />
        </ab-field>

        <ab-field :label="t('config.downloader_set.username')">
          <ab-input
            v-model="downloaderData.username"
            :aria-label="t('config.downloader_set.username')"
            autocomplete="username"
            placeholder="admin"
          />
        </ab-field>

        <ab-field :label="t('config.downloader_set.password')">
          <ab-input
            v-model="downloaderData.password"
            type="password"
            :aria-label="t('config.downloader_set.password')"
            autocomplete="current-password"
          />
        </ab-field>

        <ab-field :label="t('config.downloader_set.path')">
          <ab-input
            v-model="downloaderData.path"
            :aria-label="t('config.downloader_set.path')"
            placeholder="/downloads/Bangumi"
          />
        </ab-field>

        <ab-field :label="t('config.downloader_set.ssl')">
          <NSwitch
            v-model:value="downloaderData.ssl"
            :aria-label="t('config.downloader_set.ssl')"
          />
        </ab-field>
      </div>

      <div class="test-section">
        <ab-button
          size="sm"
          variant="secondary"
          :disabled="!canTest || isTesting"
          @click="testConnection"
        >
          {{
            isTesting
              ? t('setup.downloader.testing')
              : t('setup.downloader.test')
          }}
        </ab-button>
        <p
          v-if="testMessage"
          class="test-message"
          :class="{ success: testSuccess }"
        >
          {{ testMessage }}
        </p>
      </div>

      <p v-if="!validation.downloaderTested" class="untested-hint">
        {{ t('setup.downloader.untested_hint') }}
      </p>

      <div class="wizard-actions">
        <ab-button size="sm" variant="secondary" @click="setupStore.prevStep()">
          {{ t('setup.nav.previous') }}
        </ab-button>
        <ab-button
          variant="primary"
          size="sm"
          :disabled="!canProceed"
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

.test-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.test-message {
  font-size: 11px;
  color: var(--color-danger);
  margin: 0;

  &.success {
    color: var(--color-success);
  }
}

.untested-hint {
  font-size: 11px;
  color: var(--color-text-muted);
  margin: 0;
}

.aria2-hint {
  font-size: 11px;
  color: var(--color-text-secondary);
  margin: 0;
}

.wizard-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}
</style>
