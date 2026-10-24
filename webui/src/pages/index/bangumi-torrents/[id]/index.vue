<script lang="ts" setup>
import AbTorrentListPage from '@/components/ab-torrent-list-page.vue';
import { apiBangumi } from '@/api/bangumi';

definePage({
  name: 'Bangumi Torrents',
});

const route = useRoute('Bangumi Torrents');
const router = useRouter();
const { t } = useI18n();

// KeepAlive 会复用同一实例，路由参数必须保持响应式；非法 id 归一为 null
const bangumiId = computed(() => {
  const id = Number(route.params.id);
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

// 标题用番剧名；番剧列表尚未加载（直接打开本页）时回退为 #id。
// 标题单独计算，列表加载后只更新标题，不重建 loadFn 等回调
const { bangumi } = storeToRefs(useBangumiStore());
const title = computed(() => {
  const id = bangumiId.value;
  const name = bangumi.value.find((b) => b.id === id)?.official_title;
  return name
    ? `${name} · ${t('homepage.torrents.title')}`
    : `${t('homepage.torrents.title')} #${id}`;
});

// id 收窄后一次性构造 props，切换参数时 :key 触发重新挂载并加载
const pageProps = computed(() => {
  const id = bangumiId.value;
  if (id === null) return null;
  return {
    loadFn: () => apiBangumi.getTorrents(id),
    deleteOne: (torrentId: number) => apiBangumi.deleteTorrent(id, torrentId),
    deleteAll: () => apiBangumi.deleteAllTorrents(id),
  };
});
</script>

<template>
  <AbTorrentListPage v-if="pageProps" :key="bangumiId ?? -1" v-bind="pageProps" :title="title" />
</template>
