<script lang="ts" setup>
import { Close, Delete } from '@icon-park/vue-next';
import { useApi } from '@/hooks/useApi';
import { apiBangumi } from '@/api/bangumi';
import type { Torrent } from '#/torrent';

const props = defineProps<{
  torrents: Torrent[];
  bangumiId?: number;
  isOrphan?: boolean;
}>();

const emit = defineEmits<{
  (e: 'deleted'): void;
}>();

const { execute: execDeleteOne, isLoading: deletingOne } = useApi(
  async (torrentId: number) => {
    if (props.isOrphan) {
      return apiBangumi.deleteOrphanTorrent(torrentId);
    }
    return apiBangumi.deleteTorrent(props.bangumiId!, torrentId);
  },
  {
    showMessage: true,
    onSuccess: () => emit('deleted'),
  }
);

async function handleDeleteAll() {
  if (!confirm('确认清空所有种子？')) return;
  await execDeleteAll();
}

const { execute: execDeleteAll, isLoading: deletingAll } = useApi(
  async () => {
    if (props.isOrphan) {
      return apiBangumi.deleteOrphanTorrents();
    }
    return apiBangumi.deleteAllTorrents(props.bangumiId!);
  },
  {
    showMessage: true,
    onSuccess: () => emit('deleted'),
  }
);
</script>

<template>
  <div class="torrent-list">
    <div v-if="torrents.length === 0" class="torrent-empty">
      {{ $t('homepage.torrents.empty') }}
    </div>

    <template v-else>
      <div v-for="torrent in torrents" :key="torrent.id" class="torrent-item">
        <div class="torrent-info">
          <span class="torrent-name">{{ torrent.name }}</span>
          <div class="torrent-badges">
            <span v-if="torrent.downloaded" class="badge badge-downloaded">
              {{ $t('homepage.torrents.downloaded') }}
            </span>
            <span v-if="torrent.rss_id" class="badge badge-rss">RSS</span>
            <span v-else class="badge badge-manual">
              {{ $t('homepage.torrents.source.manual') }}
            </span>
          </div>
        </div>
        <button
          class="btn-delete"
          :disabled="deletingOne"
          :aria-label="$t('homepage.torrents.delete')"
          @click="execDeleteOne(torrent.id)"
        >
          <Close :size="14" />
        </button>
      </div>

      <div class="torrent-actions">
        <button
          class="btn-delete-all"
          :disabled="deletingAll"
          @click="handleDeleteAll()"
        >
          <Delete :size="14" />
          {{ $t('homepage.torrents.deleteAll') }}
        </button>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.torrent-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.torrent-empty {
  text-align: center;
  padding: 24px;
  color: var(--color-text-muted);
  font-size: 14px;
}

.torrent-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-hover);
  transition: background-color var(--transition-normal);
}

.torrent-info {
  flex: 1;
  min-width: 0;
}

.torrent-name {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: var(--color-text);
}

.torrent-badges {
  display: flex;
  gap: 4px;
  margin-top: 4px;
}

.badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
  line-height: 1.4;
}

.badge-downloaded {
  background: var(--color-success);
  color: var(--color-white);
}

.badge-rss {
  background: var(--color-primary);
  color: var(--color-white);
}

.badge-manual {
  background: var(--color-accent);
  color: var(--color-white);
}

.btn-delete {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  flex-shrink: 0;
  margin-left: 8px;
  transition: color var(--transition-fast), background-color var(--transition-fast);

  &:hover:not(:disabled) {
    color: var(--color-danger);
    background: rgba(239, 68, 68, 0.1);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.torrent-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 8px;
}

.btn-delete-all {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  padding: 6px 12px;
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-danger);
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast);

  &:hover:not(:disabled) {
    background: var(--color-danger);
    color: var(--color-white);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}
</style>
