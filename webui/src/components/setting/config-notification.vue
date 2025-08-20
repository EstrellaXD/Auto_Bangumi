<script lang="ts" setup>
import type { Notification } from '#/config';
import type { SettingItem } from '#/components';

const { t } = useMyI18n();
const { getSettingGroup } = useConfigStore();

const notification = getSettingGroup('notification');

const items: SettingItem<Notification>[] = [
  {
    configKey: 'enable',
    label: () => t('config.notification_set.enable'),
    type: 'switch',
    bottomLine: true,
  },
  {
    configKey: 'entry',
    label: () => t('config.notification_set.entry'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'entry',
    },
  },
];
</script>

<template>
  <ab-fold-panel :title="$t('config.notification_set.title')">
    <div space-y-12>
      <ab-setting
        v-for="i in items"
        :key="i.configKey"
        v-bind="i"
        v-model:data="notification[i.configKey]"
      ></ab-setting>
    </div>
  </ab-fold-panel>
</template>
