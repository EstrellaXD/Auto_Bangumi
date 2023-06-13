<script lang="ts" setup>
import { useI18n } from 'vue-i18n';
import type { Notification, NotificationType } from '#/config';
import type { SettingItem } from '#/components';

const { t } = useI18n({ useScope: 'global' });
const { getSettingGroup } = useConfigStore();

const notification = getSettingGroup('notification');
const notificationType: NotificationType = [
  'telegram',
  'server-chan',
  'bark',
  'wecom',
];

const items: SettingItem<Notification>[] = [
  {
    configKey: 'enable',
    label: t('config.notificationset.enable'),
    type: 'switch',
    bottomLine: true,
  },
  {
    configKey: 'type',
    label: t('config.notificationset.type'),
    type: 'select',
    css: 'w-140px',
    prop: {
      items: notificationType,
    },
  },
  {
    configKey: 'token',
    label: t('config.notificationset.token'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'token',
    },
  },
  {
    configKey: 'chat_id',
    label: t('config.notificationset.chatid'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'chat id',
    },
  },
];
</script>

<template>
  <ab-fold-panel :title="$t('config.notificationset.title')">
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
