<script lang="ts" setup>
import type { Network } from '#/config';
import type { SettingItem } from '#/components';

const { t } = useMyI18n();
const { getSettingGroup } = useConfigStore();

const network = getSettingGroup('network');

const items: SettingItem<Network>[] = [
  {
    configKey: 'tmdb_base_url',
    label: () => t('config.network_set.tmdb_base_url'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'https://api.themoviedb.org',
    },
  },
  {
    configKey: 'tmdb_api_key',
    label: () => t('config.network_set.tmdb_api_key'),
    type: 'input',
    prop: {
      type: 'password',
      autocomplete: 'off',
    },
  },
  {
    configKey: 'bgm_base_url',
    label: () => t('config.network_set.bgm_base_url'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'https://api.bgm.tv',
    },
  },
];
</script>

<template>
  <ab-fold-panel :title="$t('config.network_set.title')">
    <div space-y-8>
      <ab-setting
        v-for="i in items"
        :key="i.configKey"
        v-bind="i"
        v-model:data="network[i.configKey]"
      ></ab-setting>
    </div>
  </ab-fold-panel>
</template>
