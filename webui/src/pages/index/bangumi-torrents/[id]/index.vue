<script lang="ts" setup>
import { Close, Delete, FullSelection } from '@icon-park/vue-next';
import { apiBangumi } from '@/api/bangumi';
import { useTorrentList } from '@/hooks/useTorrentList';

definePage({
  name: 'Bangumi Torrents',
});

const route = useRoute();
const bangumiId = Number((route.params as Record<string, string>).id);

const {
  torrents, selectedIds, showConfirmClear,
  load, allSelected, toggleAll, toggleOne, runDelete,
} = useTorrentList(() => apiBangumi.getTorrents(bangumiId));

async function deleteOne(id: number) {
  await runDelete(() => apiBangumi.deleteTorrent(bangumiId, id), `已删除种子 ${id}`);
}

async function deleteSelected() {
  const ids = [...selectedIds.value];
  await runDelete(
    () => Promise.all(ids.map(id => apiBangumi.deleteTorrent(bangumiId, id))),
    `已删除 ${ids.length} 条种子`,
  );
}

async function confirmClear() {
  showConfirmClear.value = false;
  await runDelete(() => apiBangumi.deleteAllTorrents(bangumiId), `已清空番剧 ${bangumiId} 的所有种子`);
}

onActivated(load);
</script>

<template>
  <div class="page-torrents">
    <div class="toolbar">
      <h2 class="toolbar-title">{{ $t('homepage.torrents.title') }} #{{ bangumiId }}</h2>
      <div class="toolbar-actions">
        <button v-if="torrents.length > 0" class="toolbar-btn" @click="toggleAll">
          <FullSelection :size="16" />
          {{ allSelected ? '取消全选' : '全选' }}
        </button>
        <button v-if="selectedIds.size > 0" class="toolbar-btn toolbar-btn--danger" @click="deleteSelected">
          <Delete :size="16" />
          删除 ({{ selectedIds.size }})
        </button>
        <button v-if="torrents.length > 0" class="toolbar-btn toolbar-btn--danger-outline" @click="showConfirmClear = true">
          <Delete :size="16" />
          清空所有
        </button>
      </div>
    </div>

    <div v-if="torrents.length === 0" class="torrent-empty">{{ $t('homepage.torrents.empty') }}</div>
    <div v-else class="torrent-scroll">
      <div
        v-for="torrent in torrents" :key="torrent.id"
        class="torrent-item" :class="{ 'torrent-item--selected': selectedIds.has(torrent.id) }"
        @click="toggleOne(torrent.id)"
      >
        <div class="torrent-checkbox" :class="{ 'torrent-checkbox--checked': selectedIds.has(torrent.id) }">
          <svg v-if="selectedIds.has(torrent.id)" viewBox="0 0 16 16" width="12" height="12">
            <path d="M6.5 11.5L3 8l1-1 2.5 2.5L12 4l1 1z" fill="currentColor" />
          </svg>
        </div>
        <div class="torrent-info">
          <span class="torrent-name">{{ torrent.name }}</span>
          <div class="torrent-badges">
            <span v-if="torrent.downloaded" class="badge badge-downloaded">{{ $t('homepage.torrents.downloaded') }}</span>
            <span v-if="torrent.rss_id" class="badge badge-rss">RSS</span>
            <span v-else class="badge badge-manual">{{ $t('homepage.torrents.source.manual') }}</span>
          </div>
        </div>
        <button class="btn-delete" :aria-label="$t('homepage.torrents.delete')" @click.stop="deleteOne(torrent.id)">
          <Close :size="14" />
        </button>
      </div>
    </div>

    <ab-popup v-model:show="showConfirmClear" :title="$t('homepage.torrents.deleteAll')">
      <div class="confirm-body">
        <p>{{ $t('homepage.torrents.confirm_clear') }}</p>
        <div class="confirm-actions">
          <ab-button size="small" @click="showConfirmClear = false">{{ $t('common.cancel') }}</ab-button>
          <ab-button size="small" type="warn" @click="confirmClear">{{ $t('homepage.torrents.deleteAll') }}</ab-button>
        </div>
      </div>
    </ab-popup>
  </div>
</template>

<style lang="scss" scoped>
.page-torrents { display: flex; flex-direction: column; overflow: hidden; flex: 1; min-height: 0; }
.toolbar { display: flex; align-items: center; justify-content: space-between; padding: 12px; flex-shrink: 0; gap: 8px; flex-wrap: wrap; }
.toolbar-title { font-size: 16px; font-weight: 600; color: var(--color-text); margin: 0; }
.toolbar-actions { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.toolbar-btn {
  display: inline-flex; align-items: center; gap: 4px; font-size: 13px; padding: 5px 10px;
  border: 1px solid var(--color-border); border-radius: var(--radius-sm); background: transparent;
  color: var(--color-text-secondary); cursor: pointer; font-family: inherit; transition: all var(--transition-fast);
  &:hover { color: var(--color-text); border-color: var(--color-text-muted); }
  &--danger { background: var(--color-danger); border-color: var(--color-danger); color: var(--color-white); &:hover { opacity: 0.9; } }
  &--danger-outline { border-color: var(--color-danger); color: var(--color-danger); &:hover { background: var(--color-danger); color: var(--color-white); } }
}
.torrent-empty { text-align: center; padding: 48px 24px; color: var(--color-text-muted); font-size: 14px; }
.torrent-scroll { flex: 1; min-height: 0; overflow-y: auto; padding: 0 12px 12px; display: flex; flex-direction: column; gap: 6px; }
.torrent-item {
  display: flex; align-items: center; padding: 8px 12px; border-radius: var(--radius-sm);
  background: var(--color-surface-hover); cursor: pointer; transition: background-color var(--transition-fast);
  &:hover { background: color-mix(in srgb, var(--color-surface-hover) 80%, var(--color-primary)); }
  &--selected { background: color-mix(in srgb, var(--color-primary) 12%, transparent); outline: 1px solid var(--color-primary); }
}
.torrent-checkbox {
  flex-shrink: 0; width: 18px; height: 18px; border-radius: 4px; border: 2px solid var(--color-border);
  display: flex; align-items: center; justify-content: center; margin-right: 10px; transition: all var(--transition-fast); color: var(--color-white);
  &--checked { background: var(--color-primary); border-color: var(--color-primary); }
}
.torrent-info { flex: 1; min-width: 0; }
.torrent-name { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; color: var(--color-text); }
.torrent-badges { display: flex; gap: 4px; margin-top: 4px; }
.badge { font-size: 11px; padding: 1px 6px; border-radius: 3px; line-height: 1.4; }
.badge-downloaded { background: var(--color-success); color: var(--color-white); }
.badge-rss { background: var(--color-primary); color: var(--color-white); }
.badge-manual { background: var(--color-accent); color: var(--color-white); }
.btn-delete {
  display: flex; align-items: center; justify-content: center; width: 28px; height: 28px; border: none;
  border-radius: var(--radius-sm); background: transparent; color: var(--color-text-muted); cursor: pointer;
  flex-shrink: 0; margin-left: 8px; transition: color var(--transition-fast), background-color var(--transition-fast);
  &:hover { color: var(--color-danger); background: rgba(239, 68, 68, 0.1); }
}
.confirm-body { padding: 16px; }
.confirm-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
</style>
