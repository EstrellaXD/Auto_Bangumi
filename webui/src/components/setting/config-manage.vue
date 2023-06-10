<script lang="ts" setup>
import type { BangumiManage, RenameMethod } from '#/config';
import type { SettingItem } from '#/components';
import { useI18n } from 'vue-i18n';

const { t } = useI18n({ useScope: 'global' });
const { getSettingGroup } = useConfigStore();

const manage = getSettingGroup('bangumi_manage');
const renameMethod: RenameMethod = ['normal', 'pn', 'advance', 'none'];

const items: SettingItem<BangumiManage>[] = [
  {
    configKey: 'enable',
    label: t('config.manageset.enable'),
    type: 'switch',
  },
  {
    configKey: 'rename_method',
    label: t('config.manageset.method'),
    type: 'select',
    prop: {
      items: renameMethod,
    },
    bottomLine: true,
  },
  {
    configKey: 'eps_complete',
    label: t('config.manageset.eps'),
    type: 'switch',
  },
  {
    configKey: 'group_tag',
    label: t('config.manageset.grouptag'),
    type: 'switch',
  },
  {
    configKey: 'remove_bad_torrent',
    label: t('config.manageset.deletebadtorr'),
    type: 'switch',
  },
];
</script>

<template>
  <ab-fold-panel :title="$t('config.manageset.title')">
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
