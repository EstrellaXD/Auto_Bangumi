<script lang="ts" setup>
import AbTorrentListPage from '@/components/ab-torrent-list-page.vue';
import { apiBangumi } from '@/api/bangumi';

definePage({
  name: 'Orphan Torrents',
});

const { t } = useI18n();
const title = computed(() => t('homepage.others.title'));
</script>

<template>
  <AbTorrentListPage
    :title="title"
    :load-fn="() => apiBangumi.getOrphanTorrents()"
    :delete-one="(id: number) => apiBangumi.deleteOrphanTorrent(id)"
    :delete-all="() => apiBangumi.deleteOrphanTorrents()"
  />
</template>
