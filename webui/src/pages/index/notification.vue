<script setup lang="ts">
import { NButton, NDataTable, NPagination } from 'naive-ui';
import type { DataTableColumns, DataTableRowKey } from 'naive-ui';
import type { NotificationData } from '#/notification';

definePage({
  name: 'Notification',
});

const router = useRouter();
const { setRead, getNotification } = useNotificationStore();
const { total, notifications } = storeToRefs(useNotificationStore());

const columnsRef = ref<DataTableColumns<NotificationData>>([]);
const checkedRowKeysRef = ref<DataTableRowKey[]>([]);
const pageRef = ref<number>(1);
const limitRef = ref<number>(10);

onBeforeMount(() => {
  getNotification({
    page: pageRef.value,
    limit: limitRef.value,
  });
});

watch([pageRef, limitRef], () => {
  getNotification({ page: pageRef.value, limit: limitRef.value });
});

watchEffect(() => {
  if (notifications.value && notifications.value.length > 0) {
    const cols = Object.keys(omit(notifications.value[0], ['has_read'])).map(
      (key) => ({
        title: key,
        key,
      })
    );
    columnsRef.value = [
      {
        type: 'selection',
      },
      ...cols,
    ];
  }
});

function handlePageChange(newPage: number) {
  router.push({ query: { page: newPage } });
  pageRef.value = newPage;
}

function handleCheck(_: DataTableRowKey[], rows: object[]) {
  // don't use first `rowKeys` parameter, maybe this is a bug of naive-ui
  // see: https://github.com/tusen-ai/naive-ui/issues/3342
  // solved: use second `rows` parameter to filter the not null row
  const checked = (rows as NotificationData[]).filter((i) => i).map((i) => i.id);
  checkedRowKeysRef.value = checked;
}

function handleSetRead() {
  const targetIds = checkedRowKeysRef.value.map((i) => i as string);
  notifications.value = [
    ...notifications.value.filter((i) => !targetIds.includes(i.id)),
  ];
  total.value -= targetIds.length;
  setRead(targetIds);
  checkedRowKeysRef.value = [];
}
</script>

<template>
  <ab-container :title="$t('notification.title')" mt-12px min-h-screen>
    <div fx-cer flex-col justify-center space-y-4 h-full>
      <NButton
        :disabled="checkedRowKeysRef.length === 0"
        type="primary"
        tertiary
        self-start
        @click="handleSetRead"
      >
        标记为已读
      </NButton>
      <NDataTable
        :columns="columnsRef"
        :data="notifications"
        :row-key="(rowData) => rowData.id"
        :max-height="600"
        @update:checked-row-keys="handleCheck"
      />
      <NPagination
        :page="pageRef"
        :item-count="total"
        :page-size="limitRef"
        @update:page="handlePageChange"
      />
    </div>
  </ab-container>
</template>
