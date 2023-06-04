<script lang="ts" setup>
import type { Notification, NotificationType } from '#/config';
import type { SettingItem } from '#/components';

const { getSettingGroup } = useConfigStore();

const notification = getSettingGroup('notification');
const notificationType: NotificationType = ['telegram', 'server-chan', 'bark', 'wecom'];

const items: SettingItem<Notification>[] = [
  {
    configKey: 'enable',
    label: 'Enable',
    type: 'switch',
    bottomLine: true,
  },
  {
    configKey: 'type',
    label: 'Type',
    type: 'select',
    css: 'w-140px',
    prop: {
      items: notificationType,
    },
  },
  {
    configKey: 'token',
    label: 'Token',
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'token',
    },
  },
  {
    configKey: 'chat_id',
    label: 'Chat ID',
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'chat id',
    },
  },
];
</script>

<template>
  <ab-fold-panel title="Notification Setting">
    <div space-y-12px>
      <ab-setting
        v-for="i in items"
        :key="i.configKey"
        v-bind="i"
        v-model:data="notification[i.configKey]"
      ></ab-setting>
    </div>
  </ab-fold-panel>
</template>
