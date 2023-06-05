<script lang="ts" setup>
import type { Log, Program } from '#/config';
import type { SettingItem } from '#/components';

const { getSettingGroup } = useConfigStore();

const program = getSettingGroup('program');
const log = getSettingGroup('log');

const programItems: SettingItem<Program>[] = [
  {
    configKey: 'rss_time',
    label: 'Interval Time of Rss',
    type: 'input',
    css: 'w-72px',
    prop: {
      type: 'number',
      placeholder: 'port',
    },
  },
  {
    configKey: 'rename_time',
    label: 'Interval Time of Rename',
    type: 'input',
    css: 'w-72px',
    prop: {
      type: 'number',
      placeholder: 'port',
    },
  },
  {
    configKey: 'webui_port',
    label: 'WebUI Port',
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
  label: 'Debug',
  type: 'switch',
};
</script>

<template>
  <ab-fold-panel title="Normal Setting">
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
