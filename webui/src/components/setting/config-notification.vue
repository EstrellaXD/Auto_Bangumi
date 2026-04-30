<script lang="ts" setup>
import type { NotificationProviderConfig, NotificationType } from '#/config';
import type { TupleToUnion } from '#/utils';
import { apiNotification } from '@/api/notification';

const { t } = useMyI18n();
const { getSettingGroup } = useConfigStore();

const notificationRef = getSettingGroup('notification');

// Provider types with display names
const providerTypes: { value: TupleToUnion<NotificationType>; label: string }[] = [
  { value: 'telegram', label: 'Telegram' },
  { value: 'discord', label: 'Discord' },
  { value: 'bark', label: 'Bark' },
  { value: 'server-chan', label: 'Server Chan' },
  { value: 'wecom', label: 'WeChat Work' },
  { value: 'gotify', label: 'Gotify' },
  { value: 'pushover', label: 'Pushover' },
  { value: 'webhook', label: 'Webhook' },
  { value: 'onebot', label: 'OneBot v11' },
];

// Provider field configurations
const providerFields: Record<
  string,
  { key: keyof NotificationProviderConfig; label: string; placeholder: string }[]
> = {
  telegram: [
    { key: 'token', label: 'Bot Token', placeholder: 'bot token' },
    { key: 'chat_id', label: 'Chat ID', placeholder: 'chat id' },
  ],
  discord: [
    {
      key: 'webhook_url',
      label: 'Webhook URL',
      placeholder: 'https://discord.com/api/webhooks/...',
    },
  ],
  bark: [
    { key: 'device_key', label: 'Device Key', placeholder: 'device key' },
    {
      key: 'server_url',
      label: 'Server URL (optional)',
      placeholder: 'https://api.day.app',
    },
  ],
  'server-chan': [{ key: 'token', label: 'SendKey', placeholder: 'sendkey' }],
  wecom: [
    { key: 'webhook_url', label: 'Webhook URL', placeholder: 'webhook url' },
    { key: 'token', label: 'Key', placeholder: 'key' },
  ],
  gotify: [
    {
      key: 'server_url',
      label: 'Server URL',
      placeholder: 'https://gotify.example.com',
    },
    { key: 'token', label: 'App Token', placeholder: 'app token' },
  ],
  pushover: [
    { key: 'user_key', label: 'User Key', placeholder: 'user key' },
    { key: 'api_token', label: 'API Token', placeholder: 'api token' },
  ],
  webhook: [
    {
      key: 'url',
      label: 'Webhook URL',
      placeholder: 'https://example.com/webhook',
    },
    {
      key: 'template',
      label: 'Template (JSON)',
      placeholder: '{"title": "{{title}}", "episode": {{episode}}}',
    },
  ],
  onebot: [
    {
      key: 'url',
      label: 'API URL',
      placeholder: 'http://localhost:5700',
    },
    {
      key: 'token',
      label: 'Access Token (optional)',
      placeholder: 'access token',
    },
    {
      key: 'chat_id',
      label: 'Target ID (QQ/Group)',
      placeholder: '123456789',
    },
    {
      key: 'message_type',
      label: 'Message Type',
      placeholder: 'private',
    },
  ],
};

// Dialog state
const showAddDialog = ref(false);
const showEditDialog = ref(false);
const editingIndex = ref(-1);
const newProvider = ref<NotificationProviderConfig>({
  type: 'telegram',
  enabled: true,
});

// Testing state
const testingIndex = ref(-1);
const testResult = ref<{ success: boolean; message: string } | null>(null);

// Computed properties to access notification settings
const notificationEnabled = computed({
  get: () => notificationRef.value.enable,
  set: (val) => {
    notificationRef.value.enable = val;
  },
});

const providers = computed({
  get: () => notificationRef.value.providers || [],
  set: (val) => {
    notificationRef.value.providers = val;
  },
});

// Initialize providers array if not exists
if (!notificationRef.value.providers) {
  notificationRef.value.providers = [];
}

function getProviderLabel(type: string): string {
  return providerTypes.find((p) => p.value === type)?.label || type;
}

function getProviderIcon(type: string): string {
  const icons: Record<string, string> = {
    telegram: 'i-simple-icons-telegram',
    discord: 'i-simple-icons-discord',
    bark: 'i-carbon-notification',
    'server-chan': 'i-simple-icons-wechat',
    wecom: 'i-simple-icons-wechat',
    gotify: 'i-carbon-notification-filled',
    pushover: 'i-carbon-mobile',
    webhook: 'i-carbon-webhook',
    onebot: 'i-carbon-qq'
  };
  return icons[type] || 'i-carbon-notification';
}

function openAddDialog() {
  newProvider.value = {
    type: 'telegram',
    enabled: true,
  };
  testResult.value = null;
  showAddDialog.value = true;
}

function openEditDialog(index: number) {
  editingIndex.value = index;
  newProvider.value = { ...providers.value[index] };
  testResult.value = null;
  showEditDialog.value = true;
}

function addProvider() {
  const newProviders = [...providers.value, { ...newProvider.value }];
  providers.value = newProviders;
  showAddDialog.value = false;
}

function saveProvider() {
  if (editingIndex.value >= 0) {
    const newProviders = [...providers.value];
    newProviders[editingIndex.value] = { ...newProvider.value };
    providers.value = newProviders;
  }
  showEditDialog.value = false;
  editingIndex.value = -1;
}

function removeProvider(index: number) {
  const newProviders = providers.value.filter((_, i) => i !== index);
  providers.value = newProviders;
}

function toggleProvider(index: number) {
  const newProviders = [...providers.value];
  newProviders[index] = {
    ...newProviders[index],
    enabled: !newProviders[index].enabled,
  };
  providers.value = newProviders;
}

async function testProvider(index: number) {
  testingIndex.value = index;
  testResult.value = null;
  try {
    const response = await apiNotification.testProvider({ provider_index: index });
    testResult.value = {
      success: response.data.success,
      message: response.data.message_zh || response.data.message,
    };
  } catch (error: any) {
    testResult.value = {
      success: false,
      message: error.message || 'Test failed',
    };
  } finally {
    testingIndex.value = -1;
  }
}

async function testNewProvider() {
  testingIndex.value = -999; // Special index for new provider
  testResult.value = null;
  try {
    const response = await apiNotification.testProviderConfig(
      newProvider.value as any
    );
    testResult.value = {
      success: response.data.success,
      message: response.data.message_zh || response.data.message,
    };
  } catch (error: any) {
    testResult.value = {
      success: false,
      message: error.message || 'Test failed',
    };
  } finally {
    testingIndex.value = -1;
  }
}

function getFieldsForType(type: string) {
  return providerFields[type] || [];
}
</script>

<template>
  <ab-fold-panel :title="$t('config.notification_set.title')">
    <div space-y-8>
      <!-- Global enable switch -->
      <ab-setting
        config-key="enable"
        :label="() => t('config.notification_set.enable')"
        type="switch"
        v-model:data="notificationEnabled"
        bottom-line
      />

      <!-- Provider list -->
      <div v-if="notificationEnabled" space-y-8>
        <div
          v-for="(provider, index) in providers"
          :key="index"
          class="provider-item"
          :class="{ 'provider-disabled': !provider.enabled }"
        >
          <div class="provider-info">
            <div class="provider-name">
              <div :class="getProviderIcon(provider.type)" />
              {{ getProviderLabel(provider.type) }}
              <span v-if="!provider.enabled" class="disabled-badge">
                {{ $t('config.notification_set.disabled') }}
              </span>
            </div>
          </div>
          <div class="provider-actions">
            <ab-button
              size="small"
              type="secondary"
              :disabled="testingIndex === index"
              :title="$t('config.notification_set.test')"
              @click="testProvider(index)"
            >
              <div
                v-if="testingIndex === index"
                i-carbon-circle-dash
                animate-spin
              />
              <div v-else i-carbon-play />
            </ab-button>
            <ab-button
              size="small"
              type="secondary"
              :title="$t('config.notification_set.edit')"
              @click="openEditDialog(index)"
            >
              <div i-carbon-edit />
            </ab-button>
            <ab-button
              size="small"
              type="secondary"
              :title="
                provider.enabled
                  ? $t('config.notification_set.disable')
                  : $t('config.notification_set.enable_provider')
              "
              @click="toggleProvider(index)"
            >
              <div
                :class="provider.enabled ? 'i-carbon-view' : 'i-carbon-view-off'"
              />
            </ab-button>
            <ab-button
              size="small"
              type="warn"
              :title="$t('config.notification_set.remove')"
              @click="removeProvider(index)"
            >
              <div i-carbon-trash-can />
            </ab-button>
          </div>
        </div>

        <!-- Test result message -->
        <div
          v-if="testResult"
          class="test-result"
          :class="testResult.success ? 'test-success' : 'test-error'"
        >
          {{ testResult.message }}
        </div>

        <div line></div>

        <!-- Add provider button -->
        <div flex="~ justify-end">
          <ab-button size="small" type="primary" @click="openAddDialog">
            <div i-carbon-add />
            {{ $t('config.notification_set.add_provider') }}
          </ab-button>
        </div>
      </div>
    </div>

    <!-- Add Dialog -->
    <ab-popup
      v-model:show="showAddDialog"
      :title="$t('config.notification_set.add_provider')"
      css="w-400"
    >
      <div space-y-16>
        <ab-label :label="$t('config.notification_set.type')">
          <select v-model="newProvider.type" ab-input>
            <option v-for="pt in providerTypes" :key="pt.value" :value="pt.value">
              {{ pt.label }}
            </option>
          </select>
        </ab-label>

        <ab-label
          v-for="field in getFieldsForType(newProvider.type)"
          :key="field.key"
          :label="field.label"
        >
          <input
            v-if="field.key !== 'template'"
            v-model="(newProvider as any)[field.key]"
            :placeholder="field.placeholder"
            ab-input
          />
          <textarea
            v-else
            v-model="(newProvider as any)[field.key]"
            :placeholder="field.placeholder"
            ab-input
            class="field-textarea"
            rows="3"
          />
        </ab-label>

        <div
          v-if="testResult"
          class="test-result"
          :class="testResult.success ? 'test-success' : 'test-error'"
        >
          {{ testResult.message }}
        </div>

        <div line></div>

        <div flex="~ justify-between items-center">
          <ab-button
            size="small"
            type="secondary"
            :disabled="testingIndex === -999"
            @click="testNewProvider"
          >
            <div
              v-if="testingIndex === -999"
              i-carbon-circle-dash
              animate-spin
            />
            <div v-else i-carbon-play />
            {{ $t('config.notification_set.test') }}
          </ab-button>
          <div flex="~ gap-8">
            <ab-button size="small" type="warn" @click="showAddDialog = false">
              {{ $t('config.cancel') }}
            </ab-button>
            <ab-button size="small" type="primary" @click="addProvider">
              {{ $t('config.apply') }}
            </ab-button>
          </div>
        </div>
      </div>
    </ab-popup>

    <!-- Edit Dialog -->
    <ab-popup
      v-model:show="showEditDialog"
      :title="$t('config.notification_set.edit_provider')"
      css="w-400"
    >
      <div space-y-16>
        <ab-label :label="$t('config.notification_set.type')">
          <select v-model="newProvider.type" ab-input disabled>
            <option v-for="pt in providerTypes" :key="pt.value" :value="pt.value">
              {{ pt.label }}
            </option>
          </select>
        </ab-label>

        <ab-label
          v-for="field in getFieldsForType(newProvider.type)"
          :key="field.key"
          :label="field.label"
        >
          <input
            v-if="field.key !== 'template'"
            v-model="(newProvider as any)[field.key]"
            :placeholder="field.placeholder"
            ab-input
          />
          <textarea
            v-else
            v-model="(newProvider as any)[field.key]"
            :placeholder="field.placeholder"
            ab-input
            class="field-textarea"
            rows="3"
          />
        </ab-label>

        <div
          v-if="testResult"
          class="test-result"
          :class="testResult.success ? 'test-success' : 'test-error'"
        >
          {{ testResult.message }}
        </div>

        <div line></div>

        <div flex="~ justify-between items-center">
          <ab-button
            size="small"
            type="secondary"
            :disabled="testingIndex === -999"
            @click="testNewProvider"
          >
            <div
              v-if="testingIndex === -999"
              i-carbon-circle-dash
              animate-spin
            />
            <div v-else i-carbon-play />
            {{ $t('config.notification_set.test') }}
          </ab-button>
          <div flex="~ gap-8">
            <ab-button size="small" type="warn" @click="showEditDialog = false">
              {{ $t('config.cancel') }}
            </ab-button>
            <ab-button size="small" type="primary" @click="saveProvider">
              {{ $t('config.apply') }}
            </ab-button>
          </div>
        </div>
      </div>
    </ab-popup>
  </ab-fold-panel>
</template>

<style lang="scss" scoped>
.provider-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  background: var(--color-surface-elevated, #f9fafb);
  border-radius: 8px;
  transition: background-color var(--transition-normal), opacity var(--transition-normal);

  :root.dark & {
    background: var(--color-surface-elevated, #1f2937);
  }
}

.provider-disabled {
  opacity: 0.5;
}

.provider-info {
  flex: 1;
  min-width: 0;
}

.provider-name {
  font-weight: 500;
  font-size: 14px;
  color: var(--color-text);
  display: flex;
  align-items: center;
  gap: 8px;
}

.disabled-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--color-danger);
  color: white;
  opacity: 0.8;
}

.provider-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;

  :deep(.btn--small) {
    min-width: 32px;
    width: 32px;
    height: 32px;
    padding: 0;
  }

  :deep(.n-spin-container),
  :deep(.n-spin-content) {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
  }
}

.field-textarea {
  resize: none;
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
  font-size: 13px;
}

.test-result {
  font-size: 12px;
  padding: 8px 12px;
  border-radius: 6px;
}

.test-success {
  color: var(--color-success, #22c55e);
  background: color-mix(in srgb, var(--color-success, #22c55e) 10%, transparent);
}

.test-error {
  color: var(--color-danger, #ef4444);
  background: color-mix(in srgb, var(--color-danger, #ef4444) 10%, transparent);
}
</style>




