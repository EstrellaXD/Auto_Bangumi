<script lang="ts" setup>
import type {
  BangumiManage,
  RenameMethod,
  RevisionConflictPolicy,
} from '#/config';
import type { SelectItem, SettingItem } from '#/components';

const { t } = useMyI18n();
const { getSettingGroup } = useConfigStore();

const manage = getSettingGroup('bangumi_manage');
const renameMethod: RenameMethod = ['normal', 'pn', 'advance', 'none'];
const revisionConflictPolicies: RevisionConflictPolicy = ['hold', 'replace'];

const revisionConflictOptions = computed<SelectItem[]>(() => [
  {
    id: 1,
    label: t('config.manage_set.revision_conflict_hold'),
    value: revisionConflictPolicies[0],
  },
  {
    id: 2,
    label: t('config.manage_set.revision_conflict_replace'),
    value: revisionConflictPolicies[1],
  },
]);

const items = computed<SettingItem<BangumiManage>[]>(() => [
  {
    configKey: 'enable',
    label: () => t('config.manage_set.enable'),
    type: 'switch',
  },
  {
    configKey: 'rename_method',
    label: () => t('config.manage_set.method'),
    type: 'select',
    prop: {
      items: renameMethod,
    },
  },
  {
    configKey: 'revision_conflict_policy',
    label: () => t('config.manage_set.revision_conflict_policy'),
    description: t('config.manage_set.revision_conflict_hint'),
    type: 'select',
    prop: {
      items: revisionConflictOptions.value,
    },
    bottomLine: true,
  },
  {
    configKey: 'eps_complete',
    label: () => t('config.manage_set.eps'),
    type: 'switch',
  },
  {
    configKey: 'group_tag',
    label: () => t('config.manage_set.group_tag'),
    type: 'switch',
  },
  {
    configKey: 'remove_bad_torrent',
    label: () => t('config.manage_set.delete_bad_torrent'),
    type: 'switch',
  },
  {
    configKey: 'track_orphans',
    label: () => t('config.manage_set.track_orphans'),
    type: 'switch',
  },
]);
</script>

<template>
  <ab-fold-panel :title="$t('config.manage_set.title')">
    <div space-y-8>
      <ab-setting
        v-for="i in items"
        :key="i.configKey"
        v-bind="i"
        v-model:data="manage[i.configKey]"
      ></ab-setting>
    </div>
  </ab-fold-panel>
</template>
