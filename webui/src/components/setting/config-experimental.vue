<script lang="ts" setup>
import { Caution } from '@icon-park/vue-next';
import type { SettingItem } from '#/components';
import type { Experimental } from '#/config';

const { t } = useMyI18n();
const { getSettingGroup } = useConfigStore();

const experimentalFeatures = getSettingGroup('experimental');

const items: SettingItem<Experimental>[] = [
  {
    configKey: 'openai_enable',
    label: () => t('config.experimental_set.openai_enable'),
    type: 'switch',
  },
  {
    configKey: 'openai_api_key',
    label: () => t('config.experimental_set.openai_api_key'),
    type: 'input',
  },
  {
    configKey: 'openai_api_base',
    label: () => t('config.experimental_set.openai_api_base'),
    type: 'input',
  },
  {
    configKey: 'openai_model',
    label: () => t('config.experimental_set.openai_model'),
    type: 'select',
  },
];
</script>

<template>
  <ab-fold-panel :title="$t('config.experimental_set.title')">
    <div fx-cer gap-2 mb-4 p-2 bg-amber-300 rounded-4px>
      <Caution />
      <span>{{ $t('config.experimental_set.warning') }}</span>
    </div>
    <div space-y-12px>
      <ab-setting
        v-for="i in items"
        :key="i.configKey"
        v-bind="i"
        v-model:data="experimentalFeatures[i.configKey]"
      ></ab-setting>
    </div>
  </ab-fold-panel>
</template>
