<script lang="ts" setup>
import type { BangumiManage, RenameMethod } from '#/config';
import type { SettingItem } from '#/components';

const { getSettingGroup } = useConfigStore();

const manage = getSettingGroup('bangumi_manage');
const renameMethod: RenameMethod = ['normal', 'pn', 'advance', 'none'];

const items: SettingItem<BangumiManage>[] = [
  {
    configKey: 'enable',
    label: 'Enable',
    type: 'switch',
  },
  {
    configKey: 'rename_method',
    label: 'Rename Method',
    type: 'select',
    prop: {
      items: renameMethod,
    },
    bottomLine: true,
  },
  {
    configKey: 'eps_complete',
    label: 'Eps complete',
    type: 'switch',
  },
  {
    configKey: 'group_tag',
    label: 'Add Group Tag',
    type: 'switch',
  },
  {
    configKey: 'remove_bad_torrent',
    label: 'Delete Bad Torrent',
    type: 'switch',
  },
];
</script>

<template>
  <ab-fold-panel title="Manage Setting">
    <div space-y-12px>
      <ab-setting
        v-for="i in items"
        :key="i.configKey"
        v-bind="i"
        v-model:data="manage[i.configKey]"
      ></ab-setting>
    </div>
  </ab-fold-panel>
</template>
