<script lang="ts" setup>
import { Delete } from '@icon-park/vue-next';
import type { PasskeyItem } from '#/passkey';

const { t } = useMyI18n();
const { passkeys, loading, isSupported, loadPasskeys, addPasskey, deletePasskey } =
  usePasskey();

const showAddDialog = ref(false);
const deviceName = ref('');
const isRegistering = ref(false);

onMounted(() => {
  loadPasskeys();
});

function openAddDialog() {
  // 生成默认设备名称
  const platform = navigator.platform || 'Device';
  const userAgent = navigator.userAgent;

  if (userAgent.includes('iPhone')) {
    deviceName.value = 'iPhone';
  } else if (userAgent.includes('iPad')) {
    deviceName.value = 'iPad';
  } else if (userAgent.includes('Mac')) {
    deviceName.value = 'MacBook';
  } else if (userAgent.includes('Windows')) {
    deviceName.value = 'Windows PC';
  } else if (userAgent.includes('Android')) {
    deviceName.value = 'Android';
  } else {
    deviceName.value = platform;
  }

  showAddDialog.value = true;
}

async function handleAdd() {
  if (!deviceName.value.trim()) return;

  isRegistering.value = true;
  try {
    const success = await addPasskey(deviceName.value.trim());
    if (success) {
      showAddDialog.value = false;
      deviceName.value = '';
    }
  } finally {
    isRegistering.value = false;
  }
}

async function handleDelete(passkey: PasskeyItem) {
  if (!confirm(t('passkey.delete_confirm'))) return;
  await deletePasskey(passkey.id);
}

function formatDate(dateString: string | null): string {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleString();
}
</script>

<template>
  <ab-fold-panel :title="$t('passkey.title')">
    <div space-y-12>
      <!-- 不支持提示 -->
      <div v-if="!isSupported" text-orange-500 text-14>
        {{ $t('passkey.not_supported') }}
      </div>

      <!-- 加载中 -->
      <div v-else-if="loading" text-gray-500 text-14>
        {{ $t('passkey.loading') }}
      </div>

      <!-- 无 Passkey -->
      <div v-else-if="passkeys.length === 0" text-gray-500 text-14>
        {{ $t('passkey.no_passkeys') }}
      </div>

      <!-- Passkey 列表 -->
      <div v-else space-y-8>
        <div
          v-for="passkey in passkeys"
          :key="passkey.id"
          flex="~ justify-between items-center"
          p-12
          bg-gray-50
          rounded-8
        >
          <div>
            <div font-medium>{{ passkey.name }}</div>
            <div text-12 text-gray-500>
              {{ $t('passkey.created_at') }}: {{ formatDate(passkey.created_at) }}
            </div>
            <div v-if="passkey.last_used_at" text-12 text-gray-500>
              {{ $t('passkey.last_used') }}: {{ formatDate(passkey.last_used_at) }}
            </div>
            <div v-if="passkey.backup_eligible" text-12 text-green-600>
              {{ $t('passkey.synced') }}
            </div>
          </div>
          <ab-button
            size="small"
            type="warn"
            @click="handleDelete(passkey)"
          >
            <Delete size="16" />
          </ab-button>
        </div>
      </div>

      <div line></div>

      <!-- 添加按钮 -->
      <div flex="~ justify-end">
        <ab-button
          v-if="isSupported"
          size="small"
          type="primary"
          @click="openAddDialog"
        >
          {{ $t('passkey.add_new') }}
        </ab-button>
      </div>
    </div>

    <!-- 添加对话框 -->
    <ab-popup
      v-model:show="showAddDialog"
      :title="$t('passkey.register_title')"
      css="w-365"
    >
      <div space-y-16>
        <ab-label :label="$t('passkey.device_name')">
          <input
            v-model="deviceName"
            type="text"
            :placeholder="$t('passkey.device_name_placeholder')"
            ab-input
            maxlength="64"
            @keyup.enter="handleAdd"
          />
        </ab-label>

        <div text-14 text-gray-500>
          {{ $t('passkey.register_hint') }}
        </div>

        <div line></div>

        <div flex="~ justify-end gap-8">
          <ab-button
            size="small"
            type="warn"
            @click="showAddDialog = false"
          >
            {{ $t('config.cancel') }}
          </ab-button>
          <ab-button
            size="small"
            type="primary"
            :disabled="!deviceName.trim() || isRegistering"
            @click="handleAdd"
          >
            {{ $t('config.apply') }}
          </ab-button>
        </div>
      </div>
    </ab-popup>
  </ab-fold-panel>
</template>
