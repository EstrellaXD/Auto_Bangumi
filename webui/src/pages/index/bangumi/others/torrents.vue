<script lang="ts" setup>
import AbTorrentList from '@/components/ab-torrent-list.vue';
import type { Torrent } from '#/torrent';

definePage({
  name: 'Orphan Torrents',
});

const torrents = ref<Torrent[]>([]);

async function load() {
  torrents.value = await apiBangumi.getOrphanTorrents();
}

onMounted(load);
</script>

<template>
  <div class="page-container">
    <h2>{{ $t('homepage.others.title') }}</h2>
    <AbTorrentList
      :torrents="torrents"
      :is-orphan="true"
      @deleted="load"
    />
  </div>
</template>

<style lang="scss" scoped>
.page-container {
  padding: 12px;
}
</style>
