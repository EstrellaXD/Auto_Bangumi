<script lang="ts" setup>
import { Caution } from '@icon-park/vue-next';
import type { SettingItem } from '#/components';
import type { ExperimentalOpenAI, OpenAIModel, OpenAIType } from '#/config';

const { t } = useMyI18n();
const { getSettingGroup } = useConfigStore();

const openAI = getSettingGroup('experimental_openai');
const openAIModels: OpenAIModel = ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo'];
const openAITypes: OpenAIType = ['openai', 'azure'];

const providerItems: SettingItem<ExperimentalOpenAI>[] = [
  {
    configKey: 'api_type',
    label: () => t('config.experimental_openai_set.api_type'),
    type: 'select',
    prop: {
      items: openAITypes,
    },
  },
  {
    configKey: 'api_key',
    label: () => t('config.experimental_openai_set.api_key'),
    type: 'input',
    prop: {
      type: 'password',
      placeholder: 'sk-...',
    },
  },
  {
    configKey: 'api_base',
    label: () => t('config.experimental_openai_set.api_base'),
    type: 'input',
    prop: {
      type: 'url',
      placeholder: 'https://api.openai.com/v1',
    },
  },
];

const openAIItems: SettingItem<ExperimentalOpenAI>[] = [
  {
    configKey: 'model',
    label: () => t('config.experimental_openai_set.model'),
    type: 'select',
    prop: {
      items: openAIModels,
    },
  },
];

const azureItems: SettingItem<ExperimentalOpenAI>[] = [
  {
    configKey: 'api_version',
    label: () => t('config.experimental_openai_set.api_version'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: '2024-02-01',
    },
  },
  {
    configKey: 'deployment_id',
    label: () => t('config.experimental_openai_set.deployment_id'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'gpt-4o',
    },
  },
];
</script>

<template>
  <ab-fold-panel :title="$t('config.experimental_openai_set.title')">
    <div class="openai-section">
      <div class="openai-notice">
        <Caution size="16" />
        <span>{{ $t('config.experimental_openai_set.warning') }}</span>
      </div>

      <ab-setting
        config-key="enable"
        :label="() => t('config.experimental_openai_set.enable')"
        type="switch"
        v-model:data="openAI.enable"
      />

      <transition name="slide-fade">
        <div v-if="openAI.enable" class="openai-config">
          <ab-setting
            v-for="i in providerItems"
            :key="i.configKey"
            v-bind="i"
            v-model:data="openAI[i.configKey]"
          />

          <ab-setting
            v-for="i in openAI.api_type === 'azure' ? azureItems : openAIItems"
            :key="i.configKey"
            v-bind="i"
            v-model:data="openAI[i.configKey]"
          />
        </div>
      </transition>
    </div>
  </ab-fold-panel>
</template>

<style lang="scss" scoped>
.openai-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.openai-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-warning) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-warning) 30%, transparent);
  color: var(--color-warning);
  font-size: 12px;
  transition: background-color var(--transition-normal),
              border-color var(--transition-normal);
}

.openai-config {
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
