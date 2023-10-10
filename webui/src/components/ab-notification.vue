<script lang="ts" setup>
import { NBadge, NButton, NIcon, NList, NListItem, NPopover } from 'naive-ui';
import { Remind } from '@icon-park/vue-next';

const { data } = useWebSocket(
  `ws://${window.location.host}/api/v1/notification/ws`,
  {
    autoReconnect: {
      retries: 3,
      delay: 2000,
      onFailed() {
        console.error('WebSocket connection failed!');
      },
    },
  }
);

const unreadMessages = computed(() => {
  if (!data.value) {
    return [];
  }

  const json = JSON.parse(data.value);

  const messages = json.messages.map((m: any) => {
    const { title = 'AutoBangumi', content } = JSON.parse(m.data);
    return {
      id: m.message_id,
      title,
      content,
      datetime: m.datetime.toString(),
      hasRead: false,
    };
  });
  return messages;
});

const messageCount = computed(() => {
  if (!unreadMessages.value) {
    return 0;
  }
  return unreadMessages.value.length;
});
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
