<script setup lang="ts">
import { NDataTable, NPagination } from 'naive-ui';

definePage({
  name: 'Notification',
});

const router = useRouter();

const { total, page, limit, notifications } = useNotificationPage();
const columns = ref<{ title: string; key: string }[]>([]);

watchEffect(() => {
  if (notifications.value && notifications.value.length > 0) {
    columns.value = Object.keys(omit(notifications.value[0], ['has_read'])).map(
      (key) => ({
        title: key,
        key,
      })
    );
  }
});

function onUpdatePage(newPage: number) {
  router.push({ query: { page: newPage } });
  page.value = newPage;
}
</script>

<template>
  <ab-container :title="$t('notification.title')" mt-12px>
    <div fx-cer flex-col justify-center space-y-4>
      <NDataTable
        :columns="columns"
        :data="notifications"
        :row-key="(rowData) => rowData.id"
        :max-height="600"
        virtual-scroll
      />
      <NPagination
        :page="page"
        :item-count="total"
        :page-size="limit"
        @update:page="onUpdatePage"
      />
    </div>
  </ab-container>
</template>
