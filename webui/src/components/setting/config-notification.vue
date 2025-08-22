<script lang="ts" setup>
import type { Notification, NotificationType } from '#/config';
import type { SettingItem } from '#/components';

const { t } = useMyI18n();
const { getSettingGroup } = useConfigStore();

const message = useMessage();
const testLoading = ref(false);

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
    label: () => t('config.notification_set.enable'),
    type: 'switch',
    bottomLine: true,
  },
  {
    configKey: 'type',
    label: () => t('config.notification_set.type'),
    type: 'select',
    css: 'w-140',
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
];

async function testNotification() {
  console.log('Notification config:', notification);
  console.log('Notification enable status:', notification.value.enable);
  
  if (!notification.value.enable) {
    message.warning(t('config.notification_set.test_disabled'));
    return;
  }
  
  testLoading.value = true;
  try {
    // 直接导入 API 方法
    const { apiConfig } = await import('@/api/config');
    // 使用 notification.value 来获取实际值
    const notificationData = notification.value;
    console.log('Sending notification data:', notificationData);
    const res = await apiConfig.testNotification(notificationData);
    message.success(res.msg_zh || res.msg_en || 'Test notification sent successfully');
  } catch (error: any) {
    const errorMsg = error.response?.data?.msg_zh || error.response?.data?.msg_en || 'Test notification failed';
    message.error(errorMsg);
    console.error('Test notification error:', error);
  } finally {
    testLoading.value = false;
  }
}
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
      
      <div class="flex justify-end">
        <ab-button
          type="primary"
          size="normal"
          :loading="testLoading"
          :disabled="!notification.enable"
          @click="testNotification"
        >
          {{ $t('config.notification_set.test_button') }}
        </ab-button>
      </div>
    </div>
  </ab-fold-panel>
</template>
