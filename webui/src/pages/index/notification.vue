<script setup lang="ts">
import { NButton, NDataTable, NPagination } from 'naive-ui';
import type { DataTableColumns, DataTableRowKey } from 'naive-ui';
import type { Notification } from '#/notification';

definePage({
  name: 'Notification',
});

const router = useRouter();
const { total, page, limit, notifications } = useNotificationPage();
const { setRead } = useNotificationStore();
const { setReadLoading } = storeToRefs(useNotificationStore());

const columnsRef = ref<DataTableColumns<Notification>>([]);
const checkedRowKeysRef = ref<DataTableRowKey[]>([]);

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
  page.value = newPage;
}

function handleCheck(rowKeys: DataTableRowKey[], rows: object[]) {
  // filter the not null row keys
  const checked = (rows as Notification[])
    .filter((i) => i !== null)
    .map((i) => i.id);

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
        :loading="setReadLoading"
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
        :page="page"
        :item-count="total"
        :page-size="limit"
        @update:page="handlePageChange"
      />
    </div>
  </ab-container>
</template>
