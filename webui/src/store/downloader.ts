import type { QbTorrentInfo, TorrentGroup } from '#/downloader';
import type { PluginInstance } from '#/config';
import type { ApiSuccess } from '#/api';

/** 选择用的种子键：同一 hash 可能同时存在于多个下载器实例 */
export function torrentKey(t: QbTorrentInfo): string {
  return `${t.downloader_id}:${t.hash}`;
}

/** 有任一下载器实例已配置；插件提供的下载器可能没有 host 字段，视为已配置 */
export function hasConfiguredDownloader(instances: PluginInstance[]): boolean {
  return instances.some((i) => !('host' in i.options) || !!i.options.host);
}

export const useDownloaderStore = defineStore('downloader', () => {
  const torrents = shallowRef<QbTorrentInfo[]>([]);
  const selectedKeys = ref<string[]>([]);
  const loading = ref(false);

  const { downloaderData } = useEventStream();
  // SSE 已连接时使用推送数据，省去 downloader.vue 页面自己的 5s 轮询请求。
  watch(downloaderData, (data) => {
    if (data === null) return;
    torrents.value = data;
  });

  const groups = computed<TorrentGroup[]>(() => {
    const map = new Map<string, QbTorrentInfo[]>();
    for (const t of torrents.value) {
      const key = t.save_path;
      if (!map.has(key)) {
        map.set(key, []);
      }
      map.get(key)!.push(t);
    }

    const result: TorrentGroup[] = [];
    // Regex to detect season-only folder names like "Season 1", "S01", "第1季", etc.
    const seasonOnlyRegex = /^(Season\s*\d+|S\d+|第\d+季)$/i;

    for (const [savePath, items] of map) {
      const parts = savePath.replace(/\/$/, '').split('/').filter(Boolean);
      let name = parts[parts.length - 1] || savePath;
      // If the last part is just a season folder, include the parent folder too
      if (parts.length >= 2 && seasonOnlyRegex.test(name)) {
        name = `${parts[parts.length - 2]} / ${name}`;
      }
      const totalSize = items.reduce((sum, t) => sum + t.size, 0);
      const overallProgress =
        totalSize > 0
          ? items.reduce((sum, t) => sum + t.size * t.progress, 0) / totalSize
          : 0;
      result.push({
        name,
        savePath,
        totalSize,
        overallProgress,
        count: items.length,
        torrents: items.sort((a, b) => b.added_on - a.added_on),
      });
    }

    return result.sort((a, b) => a.name.localeCompare(b.name));
  });

  async function getAll() {
    loading.value = true;
    try {
      torrents.value = await apiDownloader.getTorrents();
    } catch {
      // Keep the last known list — a failed 5s poll (e.g. during a backend
      // restart) must not blank the page into a fake "no torrents" state.
    } finally {
      loading.value = false;
    }
  }

  const message = useMessage();
  const { returnUserLangMsg } = useMyI18n();

  // 部分实例失败时其它实例可能已生效，无论成败都刷新列表
  const opts = {
    showMessage: true,
    onSuccess() {
      selectedKeys.value = [];
    },
    onFinally: getAll,
  };

  /**
   * 选中的种子按所在下载器实例分组，每个实例发一次请求。
   * 每个实例都执行；任一实例请求失败或返回 status: false 时整体按失败处理，
   * 不让其它实例的成功结果掩盖它。
   */
  async function perInstance(
    run: (hashes: string[], downloaderId: string) => Promise<ApiSuccess>
  ) {
    const byInstance = new Map<string, string[]>();
    for (const t of torrents.value) {
      if (!selectedKeys.value.includes(torrentKey(t))) continue;
      const hashes = byInstance.get(t.downloader_id) ?? [];
      hashes.push(t.hash);
      byInstance.set(t.downloader_id, hashes);
    }
    const results = await Promise.allSettled(
      [...byInstance].map(([downloaderId, hashes]) => run(hashes, downloaderId))
    );
    let last: ApiSuccess | undefined;
    for (const r of results) {
      // 请求异常已由 axios 拦截器提示
      if (r.status === 'rejected') throw r.reason;
      if (r.value.status === false) {
        message.error(returnUserLangMsg(r.value));
        throw r.value;
      }
      last = r.value;
    }
    return last;
  }

  const { execute: pauseSelected } = useApi(
    () => perInstance(apiDownloader.pause),
    opts
  );
  const { execute: resumeSelected } = useApi(
    () => perInstance(apiDownloader.resume),
    opts
  );
  const { execute: deleteSelected } = useApi(
    (deleteFiles = false) =>
      perInstance((hashes, downloaderId) =>
        apiDownloader.deleteTorrents(hashes, downloaderId, deleteFiles)
      ),
    opts
  );

  function toggleKey(key: string) {
    const idx = selectedKeys.value.indexOf(key);
    if (idx === -1) {
      selectedKeys.value.push(key);
    } else {
      selectedKeys.value.splice(idx, 1);
    }
  }

  function toggleGroup(group: TorrentGroup) {
    const groupKeys = group.torrents.map(torrentKey);
    const allSelected = groupKeys.every((k) => selectedKeys.value.includes(k));
    if (allSelected) {
      selectedKeys.value = selectedKeys.value.filter(
        (k) => !groupKeys.includes(k)
      );
    } else {
      const toAdd = groupKeys.filter((k) => !selectedKeys.value.includes(k));
      selectedKeys.value.push(...toAdd);
    }
  }

  function clearSelection() {
    selectedKeys.value = [];
  }

  return {
    torrents,
    groups,
    selectedKeys,
    loading,

    getAll,
    pauseSelected,
    resumeSelected,
    deleteSelected,
    toggleKey,
    toggleGroup,
    clearSelection,
  };
});
