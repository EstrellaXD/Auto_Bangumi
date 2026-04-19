<script lang="ts" setup>
import AbTorrentListPage from '@/components/ab-torrent-list-page.vue';
import { apiBangumi } from '@/api/bangumi';

definePage({
  name: 'Bangumi Torrents',
});

const route = useRoute();
const bangumiId = Number((route.params as Record<string, string>).id);

const title = computed(() => `${useI18n().t('homepage.torrents.title')} #${bangumiId}`);
</script>

<template>
  <AbTorrentListPage
    :title="title"
    :load-fn="() => apiBangumi.getTorrents(bangumiId)"
    :delete-one="(id: number) => apiBangumi.deleteTorrent(bangumiId, id)"
    :delete-all="() => apiBangumi.deleteAllTorrents(bangumiId)"
  />
</template>
