<script lang="ts" setup>
import { Close, Delete, FullSelection } from '@icon-park/vue-next';
import { useConfirm } from '@/hooks/useConfirm';
import type { Torrent } from '#/torrent';
import { useTorrentList } from '@/hooks/useTorrentList';

const props = defineProps<{
  title: string;
  loadFn: () => Promise<Torrent[]>;
  deleteOne: (id: number) => Promise<unknown>;
  deleteAll: () => Promise<unknown>;
}>();

const {
  torrents,
  selectedIds,
  load,
  allSelected,
  toggleAll,
  toggleOne,
  runDelete,
} = useTorrentList(props.loadFn);

const { t } = useI18n();
const { confirm } = useConfirm();

async function handleDeleteOne(id: number) {
  await runDelete(
    () => props.deleteOne(id),
    t('homepage.torrents.deleted_one', { id })
  );
}

async function handleDeleteSelected() {
  const ids = [...selectedIds.value];
  await runDelete(
    () => Promise.all(ids.map((id) => props.deleteOne(id))),
    t('homepage.torrents.deleted_count', { count: ids.length })
  );
}

async function handleClearAll() {
  const ok = await confirm({
    title: t('homepage.torrents.deleteAll'),
    body: t('homepage.torrents.confirm_clear'),
    confirmText: t('homepage.torrents.deleteAll'),
    danger: true,
  });
  if (!ok) return;
  await runDelete(() => props.deleteAll(), t('homepage.torrents.cleared_all'));
}

onActivated(load);
</script>

<template>
  <div class="page-torrents">
    <div class="toolbar">
      <h2 class="toolbar-title">{{ title }}</h2>
      <div class="toolbar-actions">
        <ab-button v-if="torrents.length > 0" size="sm" @click="toggleAll">
          <template #icon>
            <FullSelection :size="14" />
          </template>
          {{
            allSelected
              ? $t('homepage.torrents.deselect_all')
              : $t('homepage.torrents.select_all')
          }}
        </ab-button>
        <ab-button
          v-if="selectedIds.size > 0"
          size="sm"
          variant="danger"
          @click="handleDeleteSelected"
        >
          <template #icon>
            <Delete :size="14" />
          </template>
          {{ $t('homepage.torrents.delete_selected', { count: selectedIds.size }) }}
        </ab-button>
        <ab-button
          v-if="torrents.length > 0"
          size="sm"
          variant="danger"
          @click="handleClearAll"
        >
          <template #icon>
            <Delete :size="14" />
          </template>
          {{ $t('homepage.torrents.deleteAll') }}
        </ab-button>
      </div>
    </div>

    <div v-if="torrents.length === 0" class="torrent-empty">
      <ab-empty :title="$t('homepage.torrents.empty')" />
    </div>
    <div v-else class="torrent-scroll">
      <div
        v-for="torrent in torrents"
        :key="torrent.id"
        class="torrent-item"
        :class="{ 'torrent-item--selected': selectedIds.has(torrent.id) }"
        @click="toggleOne(torrent.id)"
      >
        <div
          class="torrent-checkbox"
          :class="{ 'torrent-checkbox--checked': selectedIds.has(torrent.id) }"
        >
          <svg
            v-if="selectedIds.has(torrent.id)"
            viewBox="0 0 16 16"
            width="12"
            height="12"
          >
            <path d="M6.5 11.5L3 8l1-1 2.5 2.5L12 4l1 1z" fill="currentColor" />
          </svg>
        </div>
        <div class="torrent-info">
          <span class="torrent-name">{{ torrent.name }}</span>
          <div class="torrent-tags">
            <ab-tag
              v-if="torrent.downloaded"
              type="success"
              :title="$t('homepage.torrents.downloaded')"
            />
            <ab-tag v-if="torrent.rss_id" type="info" title="RSS" />
            <ab-tag
              v-else
              type="neutral"
              :title="$t('homepage.torrents.source.manual')"
            />
          </div>
        </div>
        <ab-icon-button
          size="sm"
          class="torrent-delete"
          :label="$t('homepage.torrents.delete')"
          @click.stop="handleDeleteOne(torrent.id)"
        >
          <Close :size="14" />
        </ab-icon-button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.page-torrents {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex: 1;
  min-height: 0;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  flex-shrink: 0;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.torrent-empty {
  padding: 12px;
}

.torrent-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.torrent-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-hover);
  cursor: pointer;
  transition: background-color var(--transition-fast);

  &:hover {
    background: color-mix(in srgb, var(--color-surface-hover) 80%, var(--color-primary));
  }

  &--selected {
    background: color-mix(in srgb, var(--color-primary) 12%, transparent);
    outline: 1px solid var(--color-primary);
  }
}

.torrent-checkbox {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border-radius: 4px;
  border: 2px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 10px;
  transition: all var(--transition-fast);
  color: var(--color-white);

  &--checked {
    background: var(--color-primary);
    border-color: var(--color-primary);
  }
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

.torrent-tags {
  display: flex;
  gap: 4px;
  margin-top: 4px;
}

.torrent-delete {
  margin-left: 8px;
}
</style>
