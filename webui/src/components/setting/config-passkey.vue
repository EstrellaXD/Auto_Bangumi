<script lang="ts" setup>
import { Trash } from '@lucide/vue';
import { useConfirm } from '@/hooks/useConfirm';
import type { PasskeyItem } from '#/passkey';

const { t } = useMyI18n();
const { confirm } = useConfirm();

async function onDeleteClick(passkey: PasskeyItem) {
  const ok = await confirm({
    title: t('passkey.delete'),
    body: t('passkey.delete_confirm'),
    confirmText: t('passkey.delete'),
    danger: true,
  });
  if (ok) handleDelete(passkey);
}
const {
  passkeys,
  loading,
  isSupported,
  loadPasskeys,
  addPasskey,
  deletePasskey,
} = usePasskey();

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
  await deletePasskey(passkey.id);
}

function formatDate(dateString: string | null): string {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleString();
}
</script>

<template>
  <ab-fold-panel :title="$t('passkey.title')">
    <div class="space-y-8">
      <!-- 不支持提示 -->
      <div v-if="!isSupported" class="text-orange-500 text-14">
        {{ $t('passkey.not_supported') }}
      </div>

      <!-- 加载中 -->
      <div v-else-if="loading" class="passkey-muted text-14">
        {{ $t('passkey.loading') }}
      </div>

      <!-- 无 Passkey -->
      <div v-else-if="passkeys.length === 0" class="passkey-muted text-14">
        {{ $t('passkey.no_passkeys') }}
      </div>

      <!-- Passkey 列表 -->
      <div v-else class="space-y-8">
        <div
          v-for="passkey in passkeys"
          :key="passkey.id"
          class="passkey-row"
        >
          <div>
            <div class="font-medium">
              {{ passkey.name }}
            </div>
            <div class="passkey-muted text-12">
              {{ $t('passkey.created_at') }}:
              {{ formatDate(passkey.created_at) }}
            </div>
            <div v-if="passkey.last_used_at" class="passkey-muted text-12">
              {{ $t('passkey.last_used') }}:
              {{ formatDate(passkey.last_used_at) }}
            </div>
            <ab-tag
              v-if="passkey.backup_eligible"
              type="success"
              class="passkey-synced"
              :title="$t('passkey.synced')"
            />
          </div>
          <ab-icon-button
            size="sm"
            class="passkey-delete"
            :label="$t('passkey.delete')"
            @click="onDeleteClick(passkey)"
          >
            <Trash :size="16" />
          </ab-icon-button>
        </div>
      </div>

      <div class="line" />

      <!-- 添加按钮 -->
      <div class="flex justify-end">
        <ab-button
          v-if="isSupported"
          size="sm"
          variant="primary"
          @click="openAddDialog"
        >
          {{ $t('passkey.add_new') }}
        </ab-button>
      </div>
    </div>

    <!-- 添加对话框 -->
    <ab-modal
      v-model:show="showAddDialog"
      size="sm"
      :title="$t('passkey.register_title')"
    >
      <div class="space-y-16">
        <ab-field :label="$t('passkey.device_name')">
          <ab-input
            v-model="deviceName"
            :placeholder="$t('passkey.device_name_placeholder')"
            :maxlength="64"
            @keyup.enter="handleAdd"
          />
        </ab-field>

        <div class="passkey-muted text-14">
          {{ $t('passkey.register_hint') }}
        </div>
      </div>

      <template #footer>
        <ab-button size="sm" @click="showAddDialog = false">
          {{ $t('config.cancel') }}
        </ab-button>
        <ab-button
          size="sm"
          variant="primary"
          :disabled="!deviceName.trim() || isRegistering"
          @click="handleAdd"
        >
          {{ $t('config.apply') }}
        </ab-button>
      </template>
    </ab-modal>
  </ab-fold-panel>
</template>

<style lang="scss" scoped>
// 主题色令牌：深色模式下行底与说明文字随 .dark 切换
.passkey-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--color-surface-2);
  border-radius: var(--radius-md);
}

.passkey-muted {
  color: var(--color-text-secondary);
}

.passkey-synced {
  margin-top: 4px;
}
</style>
