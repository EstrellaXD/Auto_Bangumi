<script lang="ts" setup>
import AbTorrentListPage from '@/components/ab-torrent-list-page.vue';
import { apiBangumi } from '@/api/bangumi';

definePage({
  name: 'Orphan Torrents',
});

const { t } = useI18n();
const title = computed(() => t('homepage.others.title'));
// 闭包放在脚本里：vue-tsc 3.3 把模板闭包里的导入对象误当 ref，补出 .value
const loadFn = () => apiBangumi.getOrphanTorrents();
const deleteOne = (id: number) => apiBangumi.deleteOrphanTorrent(id);
const deleteAll = () => apiBangumi.deleteOrphanTorrents();
</script>

<template>
  <AbTorrentListPage
    :title="title"
    :load-fn="loadFn"
    :delete-one="deleteOne"
    :delete-all="deleteAll"
  />
</template>
