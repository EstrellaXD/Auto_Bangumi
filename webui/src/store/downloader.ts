import type { QbTorrentInfo, TorrentGroup } from '#/downloader';

export const useDownloaderStore = defineStore('downloader', () => {
  const torrents = shallowRef<QbTorrentInfo[]>([]);
  const selectedHashes = ref<string[]>([]);
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

  const opts = {
    showMessage: true,
    onSuccess() {
      getAll();
      selectedHashes.value = [];
    },
  };

  /** 选中的种子按所在下载器实例分组，每个实例发一次请求 */
  async function perInstance<T>(
    run: (hashes: string[], downloaderId: string) => Promise<T>
  ) {
    const byInstance = new Map<string, string[]>();
    for (const t of torrents.value) {
      if (!selectedHashes.value.includes(t.hash)) continue;
      const hashes = byInstance.get(t.downloader_id) ?? [];
      hashes.push(t.hash);
      byInstance.set(t.downloader_id, hashes);
    }
    let result: T | undefined;
    for (const [downloaderId, hashes] of byInstance) {
      result = await run(hashes, downloaderId);
    }
    return result;
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

  function toggleHash(hash: string) {
    const idx = selectedHashes.value.indexOf(hash);
    if (idx === -1) {
      selectedHashes.value.push(hash);
    } else {
      selectedHashes.value.splice(idx, 1);
    }
  }

  function toggleGroup(group: TorrentGroup) {
    const groupHashes = group.torrents.map((t) => t.hash);
    const allSelected = groupHashes.every((h) =>
      selectedHashes.value.includes(h)
    );
    if (allSelected) {
      selectedHashes.value = selectedHashes.value.filter(
        (h) => !groupHashes.includes(h)
      );
    } else {
      const toAdd = groupHashes.filter(
        (h) => !selectedHashes.value.includes(h)
      );
      selectedHashes.value.push(...toAdd);
    }
  }

  function clearSelection() {
    selectedHashes.value = [];
  }

  return {
    torrents,
    groups,
    selectedHashes,
    loading,

    getAll,
    pauseSelected,
    resumeSelected,
    deleteSelected,
    toggleHash,
    toggleGroup,
    clearSelection,
  };
});
