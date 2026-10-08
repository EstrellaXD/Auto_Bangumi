import type { DownloaderInstances } from '#/downloader';
import { apiDownloader } from '@/api/downloader';

/**
 * 下载器实例列表：规则 / 订阅的下载器选择与种子列表的实例标注。
 * 每次使用时请求（设置页增删实例后无需刷新页面）；失败时保持空列表，按单实例处理。
 */
export function useDownloaderInstances() {
  const data = ref<DownloaderInstances>({ default: '', instances: [] });
  apiDownloader.instances().then(
    (value) => {
      data.value = value;
    },
    () => {}
  );
  const multiple = computed(() => data.value.instances.length > 1);
  const options = computed(() =>
    data.value.instances.map((i) => ({
      label: `${i.id} · ${i.provider}`,
      value: i.id,
    }))
  );
  return { data, multiple, options };
}
