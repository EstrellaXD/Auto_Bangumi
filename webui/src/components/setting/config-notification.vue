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
    <div space-y-4>
      <!-- Global enable switch -->
      <ab-setting
        config-key="enable"
        :label="() => t('config.notification_set.enable')"
        type="switch"
        v-model:data="notificationEnabled"
        bottom-line
      />

      <!-- Provider list -->
      <div v-if="notificationEnabled" space-y-3>
        <div
          v-for="(provider, index) in providers"
          :key="index"
          class="provider-card"
          :class="{ 'provider-disabled': !provider.enabled }"
        >
          <div flex items-center gap-3>
            <div :class="getProviderIcon(provider.type)" text-xl />
            <div flex-1>
              <div font-medium>{{ getProviderLabel(provider.type) }}</div>
              <div text-sm op-60>
                {{
                  provider.enabled
                    ? $t('config.notification_set.enabled')
                    : $t('config.notification_set.disabled')
                }}
              </div>
            </div>
            <div flex items-center gap-2>
              <button
                class="btn-icon"
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
              </button>
              <button
                class="btn-icon"
                :title="$t('config.notification_set.edit')"
                @click="openEditDialog(index)"
              >
                <div i-carbon-edit />
              </button>
              <button
                class="btn-icon"
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
              </button>
              <button
                class="btn-icon btn-danger"
                :title="$t('config.notification_set.remove')"
                @click="removeProvider(index)"
              >
                <div i-carbon-trash-can />
              </button>
            </div>
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

        <!-- Add provider button -->
        <button class="btn-add" @click="openAddDialog">
          <div i-carbon-add />
          {{ $t('config.notification_set.add_provider') }}
        </button>
      </div>
    </div>

    <!-- Add Dialog -->
    <ab-dialog
      v-model:visible="showAddDialog"
      :title="$t('config.notification_set.add_provider')"
      @confirm="addProvider"
    >
      <div space-y-4>
        <div>
          <label class="field-label">{{ $t('config.notification_set.type') }}</label>
          <select v-model="newProvider.type" class="field-input">
            <option v-for="pt in providerTypes" :key="pt.value" :value="pt.value">
              {{ pt.label }}
            </option>
          </select>
        </div>
        <div v-for="field in getFieldsForType(newProvider.type)" :key="field.key">
          <label class="field-label">{{ field.label }}</label>
          <input
            v-if="field.key !== 'template'"
            v-model="(newProvider as any)[field.key]"
            :placeholder="field.placeholder"
            class="field-input"
          />
          <textarea
            v-else
            v-model="(newProvider as any)[field.key]"
            :placeholder="field.placeholder"
            class="field-input field-textarea"
            rows="3"
          />
        </div>
        <div flex items-center justify-between>
          <button
            class="btn-test"
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
          </button>
          <div
            v-if="testResult"
            :class="testResult.success ? 'text-green-500' : 'text-red-500'"
            text-sm
          >
            {{ testResult.message }}
          </div>
        </div>
      </div>
    </ab-dialog>

    <!-- Edit Dialog -->
    <ab-dialog
      v-model:visible="showEditDialog"
      :title="$t('config.notification_set.edit_provider')"
      @confirm="saveProvider"
    >
      <div space-y-4>
        <div>
          <label class="field-label">{{ $t('config.notification_set.type') }}</label>
          <select v-model="newProvider.type" class="field-input" disabled>
            <option v-for="pt in providerTypes" :key="pt.value" :value="pt.value">
              {{ pt.label }}
            </option>
          </select>
        </div>
        <div v-for="field in getFieldsForType(newProvider.type)" :key="field.key">
          <label class="field-label">{{ field.label }}</label>
          <input
            v-if="field.key !== 'template'"
            v-model="(newProvider as any)[field.key]"
            :placeholder="field.placeholder"
            class="field-input"
          />
          <textarea
            v-else
            v-model="(newProvider as any)[field.key]"
            :placeholder="field.placeholder"
            class="field-input field-textarea"
            rows="3"
          />
        </div>
        <div flex items-center justify-between>
          <button
            class="btn-test"
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
          </button>
          <div
            v-if="testResult"
            :class="testResult.success ? 'text-green-500' : 'text-red-500'"
            text-sm
          >
            {{ testResult.message }}
          </div>
        </div>
      </div>
    </ab-dialog>
  </ab-fold-panel>
</template>

<style scoped>
.provider-card {
  @apply p-3 rounded-lg bg-gray-100 dark:bg-gray-800 transition-opacity;
}

.provider-disabled {
  @apply opacity-50;
}

.btn-icon {
  @apply p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors;
}

.btn-danger {
  @apply hover:bg-red-100 dark:hover:bg-red-900 hover:text-red-500;
}

.btn-add {
  @apply w-full p-3 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600
         flex items-center justify-center gap-2 hover:border-primary hover:text-primary
         transition-colors cursor-pointer;
}

.btn-test {
  @apply px-3 py-1.5 rounded bg-primary text-white flex items-center gap-2 hover:bg-primary-dark
         disabled:opacity-50 disabled:cursor-not-allowed transition-colors;
}

.field-label {
  @apply block text-sm font-medium mb-1;
}

.field-input {
  @apply w-full p-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800;
}

.field-textarea {
  @apply resize-none font-mono text-sm;
}

.test-result {
  @apply p-2 rounded text-sm;
}

.test-success {
  @apply bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300;
}

.test-error {
  @apply bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300;
}
</style>
