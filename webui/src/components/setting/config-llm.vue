<script lang="ts" setup>
import { Info } from '@icon-park/vue-next';
import type { SelectItem } from '#/components';
import type { LLMProvider } from '#/config';

const { t } = useMyI18n();
const { getSettingGroup } = useConfigStore();

const llm = getSettingGroup('llm');
const providers: LLMProvider = ['openai', 'anthropic', 'gemini'];

// 解析模式选项需要本地化标签，用 computed 保证语言切换时同步更新
const modeItems = computed<SelectItem[]>(() => [
  { id: 1, label: t('config.llm_set.mode_fallback'), value: 'fallback' },
  { id: 2, label: t('config.llm_set.mode_primary'), value: 'primary' },
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

          <ab-setting
            v-model:data="llm.model"
            :label="() => t('config.llm_set.model')"
            type="input"
            :prop="{ type: 'text', placeholder: 'gpt-4o-mini' }"
          />

          <!-- base_url 仅对 openai 提供商生效（自定义 OpenAI 兼容端点） -->
          <ab-setting
            v-if="llm.provider === 'openai'"
            v-model:data="llm.base_url"
            :label="() => t('config.llm_set.base_url')"
            type="input"
            :prop="{ type: 'url', placeholder: 'https://api.openai.com/v1' }"
          />
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
