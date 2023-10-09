<script lang="ts" setup>
import { NBadge, NButton, NIcon, NList, NListItem, NPopover } from 'naive-ui';
import { Remind } from '@icon-park/vue-next';
import type { Notification } from '#/notification';

// TODO: use watchEffect to subscribe topic and update messageCount
function generateNotifications(): Notification[] {
  const notifications: Notification[] = [];

  for (let i = 1; i <= 10; i++) {
    const notification: Notification = {
      id: i.toString(),
      title: `Notification ${i}`,
      content: `This is notification ${i}.`,
      datetime: new Date().toISOString().replace('T', ' ').slice(0, 19), // Get current datetime in YYYY-mm-dd HH:MM:SS format
      hasRead: false,
    };

    notifications.push(notification);
  }

  return notifications;
}

// Generate 10 fake notifications
const messages = reactive<Notification[]>(generateNotifications());
const unreadMessages = computed(() => messages.filter((m) => !m.hasRead));
const messageCount = computed(() => unreadMessages.value.length);
</script>

<template>
  <NPopover trigger="click" scrollable placement="bottom" w-400px max-h-500px>
    <template #trigger>
      <NBadge :value="messageCount" :max="99">
        <NIcon depth="1" size="24" color="white" is-btn btn-click>
          <Remind theme="outline" />
        </NIcon>
      </NBadge>
    </template>
    <NList v-if="unreadMessages.length > 0" hoverable clickable>
      <template v-for="m in unreadMessages" :key="m.id">
        <NListItem @click="m.hasRead = !m.hasRead">
          <ab-notification-item v-bind="m"></ab-notification-item>
        </NListItem>
      </template>
    </NList>
    <div v-else fx-cer justify-center py-2 h-full>
      <p text-center>没有更多消息了！</p>
    </div>
    <template v-if="unreadMessages.length > 0" #footer>
      <NButton
        text
        :bordered="false"
        :block="true"
        py-2
        @click="() => console.log('go to notification page')"
        >获取更多通知</NButton
      >
    </template>
  </NPopover>
</template>
