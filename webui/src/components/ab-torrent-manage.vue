<script lang="ts" setup>
import { Download, Delete, Refresh, Forbid } from '@icon-park/vue-next';
import { NModal, NButton, NDataTable, NTag } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import type { BangumiRule } from '#/bangumi';
import type { Torrent } from '#/torrent';
import { apiBangumi } from '@/api/bangumi';

const props = defineProps<{
  bangumi?: BangumiRule | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const { t } = useMyI18n();
const message = useMessage();

const show = defineModel('show', { default: false });
const loading = ref(false);
const torrents = ref<Torrent[]>([]);

const columns = computed((): DataTableColumns<Torrent> => [
  {
    title: t('torrent.name'),
    key: 'name',
    minWidth: 400,
    ellipsis: {
      tooltip: true
    }
  },
  {
    title: t('torrent.downloaded'),
    key: 'downloaded',
    width: 100,
    align: 'center',
    render(row: Torrent) {
      return h(
        NTag,
        {
          type: row.downloaded ? 'success' : 'default',
          size: 'small',
        },
        () => row.downloaded ? '✓' : '✗'
      );
    },
  },
  {
    title: t('torrent.renamed'),
    key: 'renamed',
    width: 100,
    align: 'center',
    render(row: Torrent) {
      return h(
        NTag,
        {
          type: row.renamed ? 'success' : 'default',
          size: 'small',
        },
        () => row.renamed ? '✓' : '✗'
      );
    },
  },
  {
    title: t('torrent.actions'),
    key: 'actions',
    width: 180,
    align: 'center',
    render(row: Torrent) {
      return h(
        'div',
        { class: 'flex gap-2 justify-center' },
        [
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              disabled: row.downloaded,
              onClick: () => handleDownload(row),
            },
            { default: () => h(Download, { size: 16 }) }
          ),
          h(
            NButton,
            {
              size: 'small',
              type: 'warning',
              disabled: row.downloaded && row.renamed,
              onClick: () => handleDisable(row),
            },
            { default: () => h(Forbid, { size: 16 }) }
          ),
          h(
            NButton,
            {
              size: 'small',
              type: 'error',
              onClick: () => handleDelete(row),
            },
            { default: () => h(Delete, { size: 16 }) }
          ),
        ]
      );
    },
  },
]);

async function fetchTorrents() {
  if (!props.bangumi?.id) return;
  
  loading.value = true;
  try {
    torrents.value = await apiBangumi.getTorrents(props.bangumi.id);
  } catch (error) {
    console.error('Failed to fetch torrents:', error);
  } finally {
    loading.value = false;
  }
}

function handleDownload(torrent: Torrent) {
  if (!props.bangumi?.id) return;
  
  useApi(apiBangumi.downloadTorrent, {
    showMessage: true,
    onSuccess() {
      fetchTorrents(); // 刷新列表
    },
  }).execute(props.bangumi.id, torrent);
}

function handleDisable(torrent: Torrent) {
  if (!props.bangumi?.id) return;
  
  useApi(apiBangumi.disableTorrent, {
    showMessage: true,
    onSuccess() {
      fetchTorrents(); // 刷新列表
    },
  }).execute(torrent.url, torrent.name, props.bangumi.id);
}

function handleDelete(torrent: Torrent) {
  useApi(apiBangumi.deleteTorrent, {
    showMessage: true,
    onSuccess() {
      fetchTorrents(); // 刷新列表
    },
  }).execute(torrent.url);
}

function close() {
  show.value = false;
  emit('close');
}

// 当对话框显示时获取数据
watch(show, (newValue) => {
  if (newValue && props.bangumi) {
    fetchTorrents();
  }
});
</script>

<template>
  <NModal 
    v-model:show="show" 
    preset="dialog" 
    :closable="false"
    :show-icon="false"
    style="width: 90vw; max-width: 1200px;"
  >

    <div class="min-h-500 max-h-700 overflow-auto">
      <div class="flex justify-between items-center mb-4">
        <div class="font-black text-gray-800" style="font-size: 24px;">
          {{ t('torrent.count', { count: torrents.length }) }}
        </div>
        <NButton 
          size="large" 
          @click="fetchTorrents" 
          :loading="loading"
        >
          <template #icon>
            <Refresh />
          </template>
          {{ t('torrent.refresh') }}
        </NButton>
      </div>

      <NDataTable
        :columns="columns"
        :data="torrents"
        :loading="loading"
        :scroll-x="800"
        size="small"
        striped
        :max-height="600"
        virtual-scroll
      />
    </div>

    <template #action>
      <NButton size="large" @click="close">
        {{ t('config.cancel') }}
      </NButton>
    </template>
  </NModal>
</template>

<style scoped>
:deep(.n-data-table-th) {
  text-align: center;
  font-weight: 800;
  font-size: 18px;
}

:deep(.n-data-table-td) {
  text-align: center;
  padding: 16px 20px;
  font-size: 17px;
}

:deep(.n-data-table-td:first-child) {
  text-align: left;
}

:deep(.n-modal) {
  margin: 20px;
}

:deep(.n-data-table-wrapper) {
  border-radius: 8px;
}

:deep(.n-data-table .n-data-table-td) {
  border-bottom: 1px solid #f0f0f0;
}

.min-h-500 {
  min-height: 500px;
}

.max-h-700 {
  max-height: 700px;
}
</style>