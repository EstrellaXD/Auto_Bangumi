<script setup lang="ts">
import { NDataTable } from 'naive-ui';
import type { PaginationProps } from 'naive-ui';

definePage({
  name: 'Notification',
});

const { notifications } = useNotification();
const columns = ref<{ title: string; key: string }[]>([]);

watchEffect(() => {
  if (notifications.value && notifications.value.length > 0) {
    columns.value = Object.keys(omit(notifications.value[0], ['hasRead'])).map(
      (key) => ({
        title: key,
        key,
      })
    );
  }
});

const pagination = reactive<PaginationProps>({
  page: 1,
  pageSize: 20,
  showSizePicker: false,
  onChange: (page: number) => {
    pagination.page = page;
  },
  onUpdatePageSize: (pageSize: number) => {
    pagination.pageSize = pageSize;
    pagination.page = 1;
  },
});
</script>

<template>
  <ab-container :title="$t('notification.title')" mt-12px>
    <NDataTable
      :columns="columns"
      :data="notifications"
      :pagination="pagination"
      :row-key="(rowData) => rowData.id"
      :max-height="600"
      virtual-scroll
    ></NDataTable>
  </ab-container>
</template>
