<script lang="ts" setup>
import AbTorrentListPage from '@/components/ab-torrent-list-page.vue';
import { apiBangumi } from '@/api/bangumi';

definePage({
  name: 'Bangumi Torrents',
});

const route = useRoute();
const router = useRouter();
const { t } = useI18n();

// KeepAlive 会复用同一实例，路由参数必须保持响应式；非法 id 归一为 null
const bangumiId = computed(() => {
  const id = Number((route.params as Record<string, string>).id);
  return Number.isInteger(id) && id > 0 ? id : null;
});

// 非法 id 不请求 API，直接回番剧列表（仅当当前仍在本页时，
// 避免 KeepAlive 缓存期间路由切换触发误跳转）
watch(
  bangumiId,
  (id) => {
    if (id === null && route.name === 'Bangumi Torrents') {
      router.replace('/bangumi');
    }
  },
  { immediate: true }
);

// id 收窄后一次性构造 props，切换参数时 :key 触发重新挂载并加载
const pageProps = computed(() => {
  const id = bangumiId.value;
  if (id === null) return null;
  return {
    title: `${t('homepage.torrents.title')} #${id}`,
    loadFn: () => apiBangumi.getTorrents(id),
    deleteOne: (torrentId: number) => apiBangumi.deleteTorrent(id, torrentId),
    deleteAll: () => apiBangumi.deleteAllTorrents(id),
  };
});
</script>

<template>
  <AbTorrentListPage v-if="pageProps" :key="bangumiId ?? -1" v-bind="pageProps" />
</template>
