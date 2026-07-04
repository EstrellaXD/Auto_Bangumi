<script lang="ts" setup>
import { Info } from '@icon-park/vue-next';
import { NSelect } from 'naive-ui';
import type { SelectOption } from 'naive-ui';
import type { SelectItem } from '#/components';
import type { LLMProvider } from '#/config';

const { t } = useMyI18n();
const message = useMessage();
const { getSettingGroup } = useConfigStore();

const llm = getSettingGroup('llm');
const providers: LLMProvider = ['openai', 'anthropic', 'gemini'];

// 解析模式选项需要本地化标签，用 computed 保证语言切换时同步更新
const modeItems = computed<SelectItem[]>(() => [
  { id: 1, label: t('config.llm_set.mode_fallback'), value: 'fallback' },
  { id: 2, label: t('config.llm_set.mode_primary'), value: 'primary' },
]);

// 模型占位符跟随所选服务商，给出各家经济型号作示例
const modelPlaceholder = computed(() => {
  const M: Record<string, string> = {
    openai: 'gpt-5-mini',
    anthropic: 'claude-haiku-4-5',
    gemini: 'gemini-2.5-flash',
  };
  return M[llm.value.provider] ?? 'gpt-5-mini';
});

// 模型列表按需从提供商 API 拉取；下拉支持搜索与自由输入（tag）
const modelOptions = ref<SelectOption[]>([]);
const modelsLoading = ref(false);
// 记录上次成功拉取时的表单指纹，凭据变化后自动重新拉取
let fetchedFor = '';

function credentialsKey(): string {
  return [llm.value.provider, llm.value.api_key, llm.value.base_url].join('|');
}

async function fetchModels() {
  if (modelsLoading.value || fetchedFor === credentialsKey()) return;
  modelsLoading.value = true;
  try {
    const models = await apiConfig.getLLMModels({
      provider: llm.value.provider,
      api_key: llm.value.api_key,
      base_url: llm.value.base_url,
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
          <ab-setting
            v-model:data="llm.provider"
            :label="() => t('config.llm_set.provider')"
            type="select"
            :prop="{ items: providers }"
          />

          <ab-setting
            v-model:data="llm.mode"
            :label="() => t('config.llm_set.mode')"
            type="select"
            :prop="{ items: modeItems }"
          />

          <ab-setting
            v-model:data="llm.api_key"
            :label="() => t('config.llm_set.api_key')"
            type="input"
            :prop="{ type: 'password', placeholder: 'sk-...' }"
          />

          <ab-label :label="() => t('config.llm_set.model')">
            <NSelect
              v-model:value="llm.model"
              class="model-select"
              filterable
              tag
              :options="modelOptions"
              :loading="modelsLoading"
              :placeholder="modelPlaceholder"
              :aria-label="t('config.llm_set.model')"
              @update:show="onModelDropdownShow"
            />
          </ab-label>

          <!-- base_url 仅对 openai 提供商生效（自定义 OpenAI 兼容端点） -->
          <ab-setting
            v-if="llm.provider === 'openai'"
            v-model:data="llm.base_url"
            :label="() => t('config.llm_set.base_url')"
            type="input"
            :prop="{ type: 'url', placeholder: 'https://api.openai.com/v1' }"
          />

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
