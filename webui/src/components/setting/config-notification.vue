<script lang="ts" setup>
import type { SettingItem } from '#/components';
import type { Notification, NotificationType } from '#/config';

const { t } = useMyI18n();
const { getSettingGroup } = useConfigStore();

const notification = getSettingGroup('notification');
const notificationType: NotificationType = [
  'telegram',
  'server-chan',
  'bark',
  'wecom',
  'gotify',
  'slack',
];

const items: SettingItem<Notification>[] = [
  {
    configKey: 'enable',
    label: () => t('config.notification_set.enable'),
    type: 'switch',
    bottomLine: true,
  },
  {
    configKey: 'type',
    label: () => t('config.notification_set.type'),
    type: 'select',
    css: 'w-140px',
    prop: {
      items: notificationType,
    },
  },
  {
    configKey: 'token',
    label: () => t('config.notification_set.token'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'token',
    },
  },
  {
    configKey: 'chat_id',
    label: () => t('config.notification_set.chat_id'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'chat id',
    },
  },
  {
    configKey: 'base_url',
    label: () => t('config.notification_set.base_url'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'e.g https://api.telegram.org',
    },
  },
  {
    configKey: 'channel',
    label: () => t('config.notification_set.channel'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'slack channel',
    },
  },
];

const isSending = ref(false);
const message = useMessage();

async function sendTestNotification() {
  isSending.value = true;
  const content = 'Hello! This is a test notification from AutoBangumi';

  let data;
  try {
    const resp = await axios.post('api/v1/notification/send', {
      content,
    });
    data = resp.data;
  } catch (error) {
    message.error(`发送失败，请检查网络和配置：${JSON.stringify(data)}`, {
      closable: true,
    });
    isSending.value = false;

    return;
  }

  message.success(`发送成功，请查验是否收到通知！`);
  isSending.value = false;
}
</script>

<template>
  <ab-fold-panel :title="$t('config.notification_set.title')">
    <div space-y-12px>
      <ab-setting
        v-for="i in items"
        :key="i.configKey"
        v-bind="i"
        v-model:data="notification[i.configKey]"
      ></ab-setting>
      <ab-button size="small" :loading="isSending" @click="sendTestNotification"
        >测试发送通知</ab-button
      >
    </div>
  </ab-fold-panel>
</template>
