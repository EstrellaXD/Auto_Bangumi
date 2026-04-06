<script lang="ts" setup>
import AbTorrentList from '@/components/ab-torrent-list.vue';
import type { Torrent } from '#/torrent';

definePage({
  name: 'Bangumi Torrents',
});

const route = useRoute();
const bangumiId = Number((route.params as Record<string, string>).id);
const torrents = ref<Torrent[]>([]);

async function load() {
  torrents.value = await apiBangumi.getTorrents(bangumiId);
}

onMounted(load);
</script>

<template>
  <div class="page-container">
    <h2>{{ $t('homepage.torrents.title') }} #{{ bangumiId }}</h2>
    <AbTorrentList
      :torrents="torrents"
      :bangumi-id="bangumiId"
      @deleted="load"
    />
  </div>
</template>

<style lang="scss" scoped>
.page-container {
  padding: 12px;
}
</style>
