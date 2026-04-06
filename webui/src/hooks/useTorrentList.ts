import { useMessage } from 'naive-ui';
import type { Torrent } from '#/torrent';

export function useTorrentList(loadFn: () => Promise<Torrent[]>) {
  const message = useMessage();
  const torrents = ref<Torrent[]>([]);
  const selectedIds = ref<Set<number>>(new Set());
  const showConfirmClear = ref(false);

  async function load() {
    try {
      torrents.value = await loadFn();
    } catch {
      torrents.value = [];
      message.error('加载种子列表失败');
    }
    selectedIds.value = new Set();
  }

  const allSelected = computed(
    () => torrents.value.length > 0 && selectedIds.value.size === torrents.value.length,
  );

  function toggleAll() {
    selectedIds.value = allSelected.value
      ? new Set()
      : new Set(torrents.value.map(t => t.id));
  }

  function toggleOne(id: number) {
    const next = new Set(selectedIds.value);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    selectedIds.value = next;
  }

  async function runDelete(fn: () => Promise<unknown>, label: string) {
    try {
      await fn();
      message.success(label);
      await load();
    } catch {
      message.error('删除失败');
    }
  }

  return {
    torrents,
    selectedIds,
    showConfirmClear,
    load,
    allSelected,
    toggleAll,
    toggleOne,
    runDelete,
    message,
  };
}
