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
  // Set 而不是响应式数组：成员判断 O(1)，整体替换触发更新
  const selectedKeys = shallowRef(new Set<string>());
  const loading = ref(false);

  const { downloaderData } = useEventStream();
  // SSE 帧计数：getAll 请求期间收到过新帧时丢弃 HTTP 结果——服务端只在
  // 负载变化时重推，旧响应覆盖新帧后已删除的种子会一直留在列表里。
  let sseFrames = 0;
  // SSE 已连接时使用推送数据，省去 downloader.vue 页面自己的 5s 轮询请求。
  watch(downloaderData, (data) => {
    if (data === null) return;
    sseFrames += 1;
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
      // 仅 Windows 路径（盘符或 UNC）按反斜杠分割；POSIX 文件夹名可含反斜杠
      const isWindows = /^([a-z]:|\\\\)/i.test(savePath);
      const parts = savePath.split(isWindows ? /[\\/]/ : '/').filter(Boolean);
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
    const frames = sseFrames;
    try {
      const data = await apiDownloader.getTorrents();
      if (frames === sseFrames) torrents.value = data;
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
      selectedKeys.value = new Set();
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
      if (!selectedKeys.value.has(torrentKey(t))) continue;
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

  function clearSelection() {
    selectedKeys.value = new Set();
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
    clearSelection,
  };
});
