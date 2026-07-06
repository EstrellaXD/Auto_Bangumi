<script lang="ts" setup>
import { Info } from '@icon-park/vue-next';
import { NSelect } from 'naive-ui';
import type { SelectGroupOption, SelectOption } from 'naive-ui';
import type { LLMProviderView } from '@/api/llm';
import type { SelectItem } from '#/components';

const { t } = useMyI18n();
const message = useMessage();
const { getSettingGroup } = useConfigStore();

const llm = getSettingGroup('llm');

// --- 提供商列表（内置 / 已安装 / 可下载）-----------------------------------
const providerList = ref<LLMProviderView[]>([]);
// 已在 /config/llm/providers 中出现的都算"可用"；不在列表里的 = 可下载插件
const KNOWN_DOWNLOADABLE: { id: string; display_name: string }[] = [
  { id: 'github-copilot', display_name: 'GitHub Copilot' },
  { id: 'codex-chatgpt', display_name: 'ChatGPT (Codex)' },
];
const busyProvider = ref('');
const providersLoaded = ref(false);

async function loadProviders() {
  try {
    providerList.value = await apiLLM.getProviders();
  } catch {
    providerList.value = [];
  } finally {
    providersLoaded.value = true;
  }
}
onMounted(loadProviders);

const selected = computed(() =>
  providerList.value.find((p) => p.id === llm.value.provider)
);
const isSubscription = computed(
  () =>
    selected.value?.auth_kind === 'oauth' ||
    selected.value?.auth_kind === 'device_code'
);
// 可下载 = 列表已加载、未在列表中、且是已知可下载插件。
const isDownloadable = computed(
  () =>
    providersLoaded.value &&
    !selected.value &&
    KNOWN_DOWNLOADABLE.some((p) => p.id === llm.value.provider)
);
// API-Key 表单：选中的是 api_key 类，或列表未加载/加载失败时的安全兜底
// （避免给内置 openai 误显示"未安装/安装"）。
const isBuiltinLike = computed(
  () =>
    selected.value?.auth_kind === 'api_key' ||
    (!selected.value && !isDownloadable.value && !isSubscription.value)
);

const providerOptions = computed<SelectGroupOption[]>(() => {
  const builtin = providerList.value.filter((p) => p.builtin);
  const installed = providerList.value.filter(
    (p) => !p.builtin && p.auth_kind === 'api_key'
  );
  const subscription = providerList.value.filter((p) => !p.builtin && p.auth_kind !== 'api_key');
  const installedIds = new Set(providerList.value.map((p) => p.id));
  const downloadable = KNOWN_DOWNLOADABLE.filter((p) => !installedIds.has(p.id));
  const groups: SelectGroupOption[] = [];
  const toOpt = (p: { id: string; display_name: string }) => ({
    label: p.display_name,
    value: p.id,
  });
  if (builtin.length)
    groups.push({ type: 'group', label: t('config.llm_set.group_builtin'), key: 'builtin', children: builtin.map(toOpt) });
  if (installed.length)
    groups.push({ type: 'group', label: t('config.llm_set.group_installed'), key: 'installed', children: installed.map(toOpt) });
  if (subscription.length)
    groups.push({ type: 'group', label: t('config.llm_set.group_subscription'), key: 'subscription', children: subscription.map(toOpt) });
  if (downloadable.length)
    groups.push({ type: 'group', label: t('config.llm_set.group_available'), key: 'available', children: downloadable.map(toOpt) });
  return groups;
});

// --- 按提供商读写凭据/模型/端点：内置写扁平字段，其它写 providers[id] -------
function fieldGet(field: 'api_key' | 'model' | 'base_url'): string {
  const pid = llm.value.provider;
  const builtin = selected.value?.builtin ?? pid === 'openai';
  if (builtin) return llm.value[field];
  return llm.value.providers?.[pid]?.[field] ?? '';
}
function fieldSet(field: 'api_key' | 'model' | 'base_url', value: string) {
  const pid = llm.value.provider;
  const builtin = selected.value?.builtin ?? pid === 'openai';
  if (builtin) {
    llm.value[field] = value;
    return;
  }
  if (!llm.value.providers) llm.value.providers = {};
  if (!llm.value.providers[pid])
    llm.value.providers[pid] = { api_key: '', model: '', base_url: '' };
  llm.value.providers[pid][field] = value;
}
const apiKey = computed({
  get: () => fieldGet('api_key'),
  set: (v: string) => fieldSet('api_key', v),
});
const model = computed({
  get: () => fieldGet('model'),
  set: (v: string) => fieldSet('model', v),
});
const baseUrl = computed({
  get: () => fieldGet('base_url'),
  set: (v: string) => fieldSet('base_url', v),
});

// 解析模式选项需要本地化标签，用 computed 保证语言切换时同步更新
const modeItems = computed<SelectItem[]>(() => [
  { id: 1, label: t('config.llm_set.mode_fallback'), value: 'fallback' },
  { id: 2, label: t('config.llm_set.mode_primary'), value: 'primary' },
]);

const modelPlaceholder = computed(
  () => selected.value?.default_model || 'gpt-5-mini'
);
const baseUrlPlaceholder = computed(
  () => selected.value?.preset_base_url || 'https://api.openai.com/v1'
);

// --- 安装 / 卸载 / 认证 -----------------------------------------------------
const showAuthDialog = ref(false);
const confirmRisk = ref(false);
const pendingInstallId = ref('');

// Copilot/Codex 属于 ToS 灰色区，安装前弹风险确认
function needsRiskNotice(id: string): boolean {
  return id === 'github-copilot' || id === 'codex-chatgpt';
}

async function onInstall(id: string) {
  if (needsRiskNotice(id) && !confirmRisk.value) {
    pendingInstallId.value = id;
    confirmRisk.value = true;
    return;
  }
  confirmRisk.value = false;
  busyProvider.value = id;
  try {
    await apiLLM.installProvider(id);
    await loadProviders();
    message.success(t('config.llm_set.install_success'));
  } catch {
    // 失败详情由通知中心呈现
    message.error(t('config.llm_set.install_failed'));
  } finally {
    busyProvider.value = '';
  }
}

async function onUninstall(id: string) {
  busyProvider.value = id;
  try {
    await apiLLM.uninstallProvider(id);
    await loadProviders();
  } catch {
    message.error(t('config.llm_set.install_failed'));
  } finally {
    busyProvider.value = '';
  }
}

async function onDisconnect(id: string) {
  await apiLLM.disconnect(id);
  await loadProviders();
}

function onAuthConnected() {
  loadProviders();
}

// --- 模型列表按需拉取（api_key 类）-----------------------------------------
const modelOptions = ref<SelectOption[]>([]);
const modelsLoading = ref(false);
let fetchedFor = '';

function credentialsKey(): string {
  return [llm.value.provider, apiKey.value, baseUrl.value].join('|');
}

async function fetchModels() {
  if (modelsLoading.value || fetchedFor === credentialsKey()) return;
  modelsLoading.value = true;
  try {
    const models = await apiConfig.getLLMModels({
      provider: llm.value.provider,
      api_key: apiKey.value,
      base_url: baseUrl.value,
    });
    modelOptions.value = models.map((m) => ({ label: m, value: m }));
    fetchedFor = credentialsKey();
  } catch {
    message.error(t('config.llm_set.models_failed'));
  } finally {
    modelsLoading.value = false;
  }
}

function onModelDropdownShow(show: boolean) {
  if (show) fetchModels();
}

watch(
  () => llm.value.provider,
  () => {
    modelOptions.value = [];
    fetchedFor = '';
  }
);

const showTuning = ref(false);

// 超时/缓存/并发/熔断调优项，收进高级折叠区
const tuningItems = computed(() => [
  { key: 'timeout' as const, label: t('config.llm_set.timeout') },
  { key: 'cache_ttl' as const, label: t('config.llm_set.cache_ttl') },
  {
    key: 'max_concurrency' as const,
    label: t('config.llm_set.max_concurrency'),
  },
  {
    key: 'failure_threshold' as const,
    label: t('config.llm_set.failure_threshold'),
  },
  {
    key: 'failure_backoff' as const,
    label: t('config.llm_set.failure_backoff'),
  },
]);
</script>

<template>
  <ab-fold-panel :title="$t('config.llm_set.title')">
    <div class="llm-section">
      <div class="llm-hint">
        <Info size="16" />
        <span>{{ $t('config.llm_set.hint') }}</span>
      </div>

      <ab-setting
        v-model:data="llm.enable"
        :label="() => t('config.llm_set.enable')"
        type="switch"
      />

      <transition name="slide-fade">
        <div v-if="llm.enable" class="llm-config">
          <ab-field :label="() => t('config.llm_set.provider')">
            <NSelect
              v-model:value="llm.provider"
              class="model-select"
              :options="providerOptions"
              :aria-label="t('config.llm_set.provider')"
            />
          </ab-field>

          <ab-setting
            v-model:data="llm.mode"
            :label="() => t('config.llm_set.mode')"
            type="select"
            :prop="{ items: modeItems }"
          />

          <!-- 订阅类提供商：连接状态 chip 或 Connect 按钮 -->
          <div v-if="isSubscription" class="llm-subscription">
            <div v-if="selected?.connected" class="llm-connected">
              <span class="llm-connected-dot" />
              <span class="llm-connected-label">{{
                t('config.llm_set.connected_as', {
                  account: selected.account_label || selected.display_name,
                })
              }}</span>
              <ab-button size="sm" variant="ghost" @click="onDisconnect(selected.id)">{{
                t('config.llm_set.disconnect')
              }}</ab-button>
            </div>
            <ab-button
              v-else
              variant="primary"
              size="sm"
              @click="showAuthDialog = true"
              >{{ t('config.llm_set.connect') }}</ab-button
            >
          </div>

          <!-- api_key 类（内置 + 预设）：密钥 + 模型 + base_url -->
          <template v-if="isBuiltinLike">
            <ab-setting
              v-model:data="apiKey"
              :label="() => t('config.llm_set.api_key')"
              type="input"
              :prop="{ type: 'password', placeholder: 'sk-...' }"
            />

            <ab-field :label="() => t('config.llm_set.model')">
              <NSelect
                v-model:value="model"
                class="model-select"
                filterable
                tag
                :options="modelOptions"
                :loading="modelsLoading"
                :placeholder="modelPlaceholder"
                :aria-label="t('config.llm_set.model')"
                @update:show="onModelDropdownShow"
              />
            </ab-field>

            <ab-setting
              v-if="selected?.needs_base_url"
              v-model:data="baseUrl"
              :label="() => t('config.llm_set.base_url')"
              type="input"
              :prop="{ type: 'url', placeholder: baseUrlPlaceholder }"
            />
          </template>

          <!-- 可下载插件：安装按钮（灰色插件先弹风险确认） -->
          <div v-if="isDownloadable" class="llm-install">
            <p class="llm-install-hint">
              {{ t('config.llm_set.not_installed') }}
            </p>
            <ab-button
              v-if="!confirmRisk"
              variant="primary"
              size="sm"
              :loading="busyProvider === llm.provider"
              @click="onInstall(llm.provider)"
              >{{ t('config.llm_set.install') }}</ab-button
            >
            <div v-else class="llm-risk">
              <p class="llm-risk-text">{{ t('config.llm_set.risk_notice') }}</p>
              <div class="llm-risk-actions">
                <ab-button size="sm" variant="secondary" @click="confirmRisk = false">{{
                  t('config.llm_set.risk_cancel')
                }}</ab-button>
                <ab-button
                  variant="danger"
                  size="sm"
                  :loading="busyProvider === llm.provider"
                  @click="onInstall(llm.provider)"
                  >{{ t('config.llm_set.risk_confirm') }}</ab-button
                >
              </div>
            </div>
          </div>

          <!-- 已安装的非内置提供商：卸载入口 -->
          <div
            v-if="selected && !selected.builtin && selected.plugin_version"
            class="llm-uninstall"
          >
            <ab-button
              size="sm"
              variant="danger"
              :loading="busyProvider === selected.id"
              @click="onUninstall(selected.id)"
              >{{ t('config.llm_set.uninstall') }}</ab-button
            >
          </div>

          <!-- 超时/缓存/并发/熔断调优项 -->
          <advanced-section v-model:open="showTuning">
            <ab-setting
              v-for="item in tuningItems"
              :key="item.key"
              v-model:data="llm[item.key]"
              :label="() => item.label"
              type="input"
              css="w-72"
              :prop="{ type: 'number', min: 0 }"
            />
          </advanced-section>
        </div>
      </transition>
    </div>

    <llm-auth-dialog
      v-if="selected"
      v-model:show="showAuthDialog"
      :provider-id="selected.id"
      :display-name="selected.display_name"
      @connected="onAuthConnected"
    />
  </ab-fold-panel>
</template>

<style lang="scss" scoped>
.llm-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.llm-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-primary) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-primary) 25%, transparent);
  color: var(--color-text-secondary);
  font-size: 12px;
  transition: background-color var(--transition-normal),
              border-color var(--transition-normal);
}

.llm-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 4px;
}

.model-select {
  @include forTablet {
    max-width: 260px;
  }
}

.llm-subscription,
.llm-install,
.llm-uninstall {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.llm-connected {
  display: flex;
  align-items: center;
  gap: 8px;
}

.llm-connected-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-success, #22c55e);
}

.llm-connected-label {
  font-size: 13px;
  color: var(--color-text);
}

.llm-install-hint {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.llm-risk {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: 1px solid var(--color-border);
}

.llm-risk-text {
  font-size: 12.5px;
  color: var(--color-text);
}

.llm-risk-actions {
  display: flex;
  gap: 8px;
}

.slide-fade-enter-active {
  transition: all 0.2s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.15s ease-in;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
