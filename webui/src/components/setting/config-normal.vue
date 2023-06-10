<script lang="ts" setup>
import type { Log, Program } from '#/config';
import type { SettingItem } from '#/components';
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
const { getSettingGroup } = useConfigStore();

const program = getSettingGroup('program');
const log = getSettingGroup('log');

const programItems: SettingItem<Program>[] = [
  {
    configKey: 'rss_time',
    label: t('config.normalset.rssintvl'),
    type: 'input',
    css: 'w-72px',
    prop: {
      type: 'number',
      placeholder: 'port',
    },
  },
  {
    configKey: 'rename_time',
    label: t('config.normalset.renameintvl'),
    type: 'input',
    css: 'w-72px',
    prop: {
      type: 'number',
      placeholder: 'port',
    },
  },
  {
    configKey: 'webui_port',
    label: t('config.normalset.webport'),
    type: 'input',
    css: 'w-72px',
    prop: {
      type: 'number',
      placeholder: 'port',
    },
    bottomLine: true,
  },
];

const logItems: SettingItem<Log> = {
  configKey: 'debug_enable',
  label: t('config.normalset.debug'),
  type: 'switch',
};
</script>

<template>
  <ab-fold-panel :title="$t('config.normalset.title')">
    <div space-y-12px>
      <ab-setting
        v-for="i in programItems"
        :key="i.configKey"
        v-bind="i"
        v-model:data="program[i.configKey]"
      ></ab-setting>

      <ab-setting
        v-bind="logItems"
        v-model:data="log[logItems.configKey]"
      ></ab-setting>
    </div>
  </ab-fold-panel>
</template>
