<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue';
import { storeToRefs } from 'pinia';
import type { TokenScope, UserPublic } from '#/access';
import { useAccessStore } from '@/store/access';
import { useMessage } from '@/hooks/useMessage';
import { useMyI18n } from '@/hooks/useMyI18n';
import { useConfirm } from '@/hooks/useConfirm';

const store = useAccessStore();
const { users, tokens, loading } = storeToRefs(store);
const { t } = useMyI18n();
const message = useMessage();
const { confirm } = useConfirm();

const showUserDialog = ref(false);
const showTokenDialog = ref(false);
const showTokenValue = ref(false);
const username = ref('');
const password = ref('');
const tokenName = ref('');
const tokenScope = ref<TokenScope>('api');
const issuedToken = ref('');
const submitting = ref(false);

const activeTokens = computed(() =>
  tokens.value.filter((token) => token.revoked_at === null)
);

onMounted(() => {
  store.load().catch(() => undefined);
});

async function handleCreateUser(): Promise<void> {
  if (!username.value.trim() || password.value.length < 8) return;
  submitting.value = true;
  try {
    await store.createUser({
      username: username.value.trim(),
      password: password.value,
    });
    username.value = '';
    password.value = '';
    showUserDialog.value = false;
    message.success(t('access.user_created'));
  } finally {
    submitting.value = false;
  }
}

async function toggleUser(user: UserPublic): Promise<void> {
  await store.updateUser(user.id, { enabled: !user.enabled });
}

async function deleteUser(user: UserPublic): Promise<void> {
  const confirmed = await confirm({
    title: t('access.delete_user_confirm', { username: user.username }),
    confirmText: t('access.delete'),
    danger: true,
  });
  if (!confirmed) return;
  await store.deleteUser(user.id);
}

async function handleCreateToken(): Promise<void> {
  if (!tokenName.value.trim()) return;
  submitting.value = true;
  try {
    issuedToken.value = await store.createToken(
      tokenName.value.trim(),
      tokenScope.value
    );
    tokenName.value = '';
    showTokenDialog.value = false;
    showTokenValue.value = true;
  } finally {
    submitting.value = false;
  }
}

async function copyIssuedToken(): Promise<void> {
  await navigator.clipboard.writeText(issuedToken.value);
  message.success(t('access.token_copied'));
}

async function revokeToken(tokenId: number): Promise<void> {
  const confirmed = await confirm({
    title: t('access.revoke_token_confirm'),
    confirmText: t('access.revoke'),
    danger: true,
  });
  if (!confirmed) return;
  await store.revokeToken(tokenId);
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : t('access.never');
}
</script>

<template>
  <ab-fold-panel :title="$t('access.title')">
    <div class="access-section">
      <div class="section-heading">
        <div>
          <h3>{{ $t('access.users') }}</h3>
          <p>{{ $t('access.users_hint') }}</p>
        </div>
        <ab-button size="sm" @click="showUserDialog = true">
          {{ $t('access.add_user') }}
        </ab-button>
      </div>

      <div v-if="loading" class="empty-state">{{ $t('access.loading') }}</div>
      <div v-else class="access-list">
        <div v-for="user in users" :key="user.id" class="access-row">
          <div class="row-main">
            <strong>{{ user.username }}</strong>
            <span class="status-dot" :class="[{ disabled: !user.enabled }]">
              {{ user.enabled ? $t('access.enabled') : $t('access.disabled') }}
            </span>
          </div>
          <div class="row-actions">
            <ab-switch
              :model-value="user.enabled"
              :aria-label="
                $t('access.toggle_user', { username: user.username })
              "
              @update:model-value="toggleUser(user)"
            />
            <ab-button size="sm" variant="danger" @click="deleteUser(user)">
              {{ $t('access.delete') }}
            </ab-button>
          </div>
        </div>
      </div>
    </div>

    <div class="divider" />

    <div class="access-section">
      <div class="section-heading">
        <div>
          <h3>{{ $t('access.tokens') }}</h3>
          <p>{{ $t('access.tokens_hint') }}</p>
        </div>
        <ab-button size="sm" @click="showTokenDialog = true">
          {{ $t('access.add_token') }}
        </ab-button>
      </div>

      <div v-if="activeTokens.length === 0" class="empty-state">
        {{ $t('access.no_tokens') }}
      </div>
      <div v-else class="access-list">
        <div v-for="token in activeTokens" :key="token.id" class="access-row">
          <div class="token-info">
            <div class="row-main">
              <strong>{{ token.name }}</strong>
              <span class="scope-badge">{{ token.scope.toUpperCase() }}</span>
            </div>
            <code>{{ token.prefix }}…</code>
            <small>
              {{ $t('access.last_used') }}: {{ formatDate(token.last_used_at) }}
            </small>
          </div>
          <ab-button size="sm" variant="danger" @click="revokeToken(token.id)">
            {{ $t('access.revoke') }}
          </ab-button>
        </div>
      </div>
    </div>

    <ab-modal
      v-model:show="showUserDialog"
      size="sm"
      :title="$t('access.add_user')"
    >
      <div class="dialog-form">
        <ab-field :label="$t('access.username')">
          <ab-input v-model="username" autocomplete="off" :maxlength="20" />
        </ab-field>
        <ab-field :label="$t('access.password')">
          <ab-input
            v-model="password"
            type="password"
            autocomplete="new-password"
          />
        </ab-field>
      </div>
      <template #footer>
        <ab-button size="sm" @click="showUserDialog = false">
          {{ $t('config.cancel') }}
        </ab-button>
        <ab-button
          size="sm"
          variant="primary"
          :loading="submitting"
          :disabled="!username.trim() || password.length < 8"
          @click="handleCreateUser"
        >
          {{ $t('access.create') }}
        </ab-button>
      </template>
    </ab-modal>

    <ab-modal
      v-model:show="showTokenDialog"
      size="sm"
      :title="$t('access.add_token')"
    >
      <div class="dialog-form">
        <ab-field :label="$t('access.token_name')">
          <ab-input v-model="tokenName" :maxlength="64" />
        </ab-field>
        <ab-field :label="$t('access.token_scope')">
          <ab-select
            v-model="tokenScope"
            :options="[
              { label: 'API', value: 'api' },
              { label: 'MCP', value: 'mcp' },
            ]"
          />
        </ab-field>
      </div>
      <template #footer>
        <ab-button size="sm" @click="showTokenDialog = false">
          {{ $t('config.cancel') }}
        </ab-button>
        <ab-button
          size="sm"
          variant="primary"
          :loading="submitting"
          :disabled="!tokenName.trim()"
          @click="handleCreateToken"
        >
          {{ $t('access.create') }}
        </ab-button>
      </template>
    </ab-modal>

    <ab-modal v-model:show="showTokenValue" :title="$t('access.token_created')">
      <div class="token-reveal">
        <p>{{ $t('access.token_once') }}</p>
        <code>{{ issuedToken }}</code>
      </div>
      <template #footer>
        <ab-button size="sm" variant="primary" @click="copyIssuedToken">
          {{ $t('access.copy') }}
        </ab-button>
      </template>
    </ab-modal>
  </ab-fold-panel>
</template>

<style lang="scss" scoped>
.access-section,
.dialog-form,
.token-reveal {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-heading,
.access-row,
.row-main,
.row-actions {
  display: flex;
  align-items: center;
}

.section-heading,
.access-row {
  justify-content: space-between;
  gap: 12px;
}

.section-heading h3 {
  margin: 0 0 4px;
  font-size: 14px;
}

.section-heading p,
.empty-state,
.token-info small {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 12px;
}

.access-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.access-row {
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.row-main,
.row-actions {
  gap: 8px;
}

.status-dot,
.scope-badge {
  padding: 2px 7px;
  border-radius: var(--radius-full);
  color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 12%, transparent);
  font-size: 11px;
}

.status-dot.disabled {
  color: var(--color-text-secondary);
  background: var(--color-surface-hover);
}

.token-info {
  min-width: 0;
}

.token-info code,
.token-reveal code {
  display: block;
  overflow-wrap: anywhere;
  color: var(--color-text-secondary);
}

.divider {
  height: 1px;
  margin: 16px 0;
  background: var(--color-border);
}

.token-reveal p {
  margin: 0;
  color: var(--color-danger);
}

@media (max-width: 520px) {
  .section-heading,
  .access-row {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
