<script lang="ts" setup>
import { NBadge, NButton, NIcon, NList, NListItem, NPopover } from 'naive-ui';
import { Remind } from '@icon-park/vue-next';

const router = useRouter();

const { onUpdate, offUpdate } = useNotificationStore();
const { total, top10Notifications } = storeToRefs(useNotificationStore());

onBeforeMount(() => {
  onUpdate();
});

onUnmounted(() => {
  offUpdate();
});
</script>

<template>
  <NPopover trigger="click" scrollable placement="bottom" w-400px max-h-500px>
    <template #trigger>
      <NBadge :value="total" :max="99">
        <NIcon depth="1" size="24" color="white" is-btn btn-click>
          <Remind theme="outline" />
        </NIcon>
      </NBadge>
    </template>
    <NList v-if="top10Notifications.length > 0" hoverable clickable>
      <template v-for="m in top10Notifications" :key="m.id">
        <NListItem @click="m.has_read = !m.has_read">
          <ab-notification-item v-bind="m"></ab-notification-item>
        </NListItem>
      </template>
    </NList>
    <div v-else fx-cer justify-center py-2 h-full>
      <p text-center>没有更多消息了！</p>
    </div>
    <template v-if="total" #footer>
      <NButton
        text
        :bordered="false"
        :block="true"
        py-2
        @click="router.push({ path: '/notification' })"
        >获取更多通知</NButton
      >
    </template>
  </NPopover>
</template>
