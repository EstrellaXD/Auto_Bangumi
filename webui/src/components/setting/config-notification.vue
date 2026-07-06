<script lang="ts" setup>
import { NSelect } from 'naive-ui';
import { useConfirm } from '@/hooks/useConfirm';
import type { NotificationProviderConfig, NotificationType } from '#/config';
import type { TupleToUnion } from '#/utils';
import { apiNotification } from '@/api/notification';

const { t, returnUserLangText } = useMyI18n();
const { confirm } = useConfirm();
const { getSettingGroup } = useConfigStore();

const notificationRef = getSettingGroup('notification');

// Provider types with display names
const providerTypes: {
  value: TupleToUnion<NotificationType>;
  label: string;
}[] = [
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
  {
    key: keyof NotificationProviderConfig;
    label: string;
    placeholder: string;
  }[]
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

async function onRemoveProvider(index: number) {
  const ok = await confirm({
    title: t('config.notification_set.remove'),
    body: t('config.notification_set.remove_confirm'),
    confirmText: t('config.notification_set.remove'),
    danger: true,
  });
  if (ok) removeProvider(index);
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
    const response = await apiNotification.testProvider({
      provider_index: index,
    });
    testResult.value = {
      success: response.data.success,
      message: returnUserLangText({
        en: response.data.message_en,
        'zh-CN': response.data.message_zh,
      }),
    };
  } catch {
    testResult.value = {
      success: false,
      message: t('config.notification_set.test_failed'),
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
      message: returnUserLangText({
        en: response.data.message_en,
        'zh-CN': response.data.message_zh,
      }),
    };
  } catch {
    testResult.value = {
      success: false,
      message: t('config.notification_set.test_failed'),
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
        v-model:data="notificationEnabled"
        config-key="enable"
        :label="() => t('config.notification_set.enable')"
        type="switch"
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
            <ab-icon-button
              size="sm"
              :disabled="testingIndex === index"
              :label="$t('config.notification_set.test')"
              @click="testProvider(index)"
            >
              <div
                v-if="testingIndex === index"
                i-carbon-circle-dash
                animate-spin
              />
              <div v-else i-carbon-play />
            </ab-icon-button>
            <ab-icon-button
              size="sm"
              :label="$t('config.notification_set.edit')"
              @click="openEditDialog(index)"
            >
              <div i-carbon-edit />
            </ab-icon-button>
            <ab-icon-button
              size="sm"
              :label="
                provider.enabled
                  ? $t('config.notification_set.disable')
                  : $t('config.notification_set.enable_provider')
              "
              @click="toggleProvider(index)"
            >
              <div
                :class="
                  provider.enabled ? 'i-carbon-view' : 'i-carbon-view-off'
                "
              />
            </ab-icon-button>
            <ab-icon-button
              size="sm"
              class="provider-remove"
              :label="$t('config.notification_set.remove')"
              @click="onRemoveProvider(index)"
            >
              <div i-carbon-trash-can />
            </ab-icon-button>
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
          <ab-button size="sm" variant="primary" @click="openAddDialog">
            <div i-carbon-add />
            {{ $t('config.notification_set.add_provider') }}
          </ab-button>
        </div>
      </div>
    </div>

    <!-- Add Dialog -->
    <ab-modal
      v-model:show="showAddDialog"
      size="sm"
      :title="$t('config.notification_set.add_provider')"
    >
      <div space-y-16>
        <ab-field :label="$t('config.notification_set.type')">
          <NSelect
            v-model:value="newProvider.type"
            :options="providerTypes"
            class="provider-type-select"
          />
        </ab-field>

        <ab-field
          v-for="field in getFieldsForType(newProvider.type)"
          :key="field.key"
          :label="field.label"
        >
          <ab-input
            v-if="field.key !== 'template'"
            v-model="(newProvider as any)[field.key]"
            :placeholder="field.placeholder"
          />
          <textarea
            v-else
            v-model="(newProvider as any)[field.key]"
            :placeholder="field.placeholder"
            class="field-textarea"
            rows="3"
          />
        </ab-field>

        <div
          v-if="testResult"
          class="test-result"
          :class="testResult.success ? 'test-success' : 'test-error'"
        >
          {{ testResult.message }}
        </div>

      </div>

      <template #footer>
        <ab-button
          size="sm"
          class="footer-test"
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
        <ab-button size="sm" @click="showAddDialog = false">
          {{ $t('config.cancel') }}
        </ab-button>
        <ab-button size="sm" variant="primary" @click="addProvider">
          {{ $t('config.apply') }}
        </ab-button>
      </template>
    </ab-modal>

    <!-- Edit Dialog -->
    <ab-modal
      v-model:show="showEditDialog"
      size="sm"
      :title="$t('config.notification_set.edit_provider')"
    >
      <div space-y-16>
        <ab-field :label="$t('config.notification_set.type')">
          <NSelect
            v-model:value="newProvider.type"
            :options="providerTypes"
            disabled
            class="provider-type-select"
          />
        </ab-field>

        <ab-field
          v-for="field in getFieldsForType(newProvider.type)"
          :key="field.key"
          :label="field.label"
        >
          <ab-input
            v-if="field.key !== 'template'"
            v-model="(newProvider as any)[field.key]"
            :placeholder="field.placeholder"
          />
          <textarea
            v-else
            v-model="(newProvider as any)[field.key]"
            :placeholder="field.placeholder"
            class="field-textarea"
            rows="3"
          />
        </ab-field>

        <div
          v-if="testResult"
          class="test-result"
          :class="testResult.success ? 'test-success' : 'test-error'"
        >
          {{ testResult.message }}
        </div>

      </div>

      <template #footer>
        <ab-button
          size="sm"
          class="footer-test"
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
        <ab-button size="sm" @click="showEditDialog = false">
          {{ $t('config.cancel') }}
        </ab-button>
        <ab-button size="sm" variant="primary" @click="saveProvider">
          {{ $t('config.apply') }}
        </ab-button>
      </template>
    </ab-modal>
  </ab-fold-panel>
</template>

<style lang="scss" scoped>
.provider-type-select {
  width: 200px;
  max-width: 100%;
}

.provider-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  background: var(--color-surface-elevated, #f9fafb);
  border-radius: 8px;
  transition: background-color var(--transition-normal),
    opacity var(--transition-normal);

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

  .provider-remove {
    color: var(--color-danger);

    &:hover:not(:disabled) {
      color: var(--color-danger);
      background: color-mix(in srgb, var(--color-danger) 12%, transparent);
    }
  }
}

.footer-test {
  margin-right: auto;
}

.field-textarea {
  // Soft Ink 填充式多行输入（ab-input 组件暂不支持 textarea）
  width: 100%;
  padding: 8px 11px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: var(--color-surface-2);
  color: var(--color-text);
  outline: none;
  resize: none;
  font-family: var(--font-mono);
  font-size: 13px;
  transition: border-color var(--transition-fast),
    background-color var(--transition-fast), box-shadow var(--transition-fast);

  &:focus {
    background: var(--color-surface);
    border-color: var(--color-primary);
    box-shadow: 0 0 0 2px var(--color-primary-alpha);
  }

  @include forTablet {
    width: 220px;
  }
}

.test-result {
  font-size: 12px;
  padding: 8px 12px;
  border-radius: 6px;
}

.test-success {
  color: var(--color-success, #22c55e);
  background: color-mix(
    in srgb,
    var(--color-success, #22c55e) 10%,
    transparent
  );
}

.test-error {
  color: var(--color-danger, #ef4444);
  background: color-mix(in srgb, var(--color-danger, #ef4444) 10%, transparent);
}
</style>
