import type { QbTorrentInfo, TorrentGroup } from '#/downloader';

export const useDownloaderStore = defineStore('downloader', () => {
  const torrents = shallowRef<QbTorrentInfo[]>([]);
  const selectedHashes = ref<string[]>([]);
  const loading = ref(false);

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
      torrents.value = [];
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

  const { execute: pauseSelected } = useApi(
    () => apiDownloader.pause(selectedHashes.value),
    opts
  );
  const { execute: resumeSelected } = useApi(
    () => apiDownloader.resume(selectedHashes.value),
    opts
  );
  const { execute: deleteSelected } = useApi(
    (deleteFiles = false) =>
      apiDownloader.deleteTorrents(selectedHashes.value, deleteFiles),
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
