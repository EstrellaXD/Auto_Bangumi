<script lang="ts" setup>
import { Close, Delete, FullSelection, More } from '@icon-park/vue-next';
import { useConfirm } from '@/hooks/useConfirm';
import type { Torrent } from '#/torrent';
import { useTorrentList } from '@/hooks/useTorrentList';
import type { AbMenuItem } from '@/components/basic/ab-menu.vue';

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
const { isMobile } = useBreakpointQuery();

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

const mobileOverflowActions = computed<AbMenuItem[]>(() => [
  {
    key: 'clear-all',
    label: () => t('homepage.torrents.deleteAll'),
    icon: Delete,
    danger: true,
    handler: handleClearAll,
  },
]);

onActivated(load);
</script>

<template>
  <div class="page-torrents">
    <div class="toolbar">
      <h2 class="toolbar-title">{{ title }}</h2>
      <div v-if="!isMobile" class="toolbar-actions">
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
          class="torrent-delete-selected"
          @click="handleDeleteSelected"
        >
          <template #icon>
            <Delete :size="14" />
          </template>
          {{
            $t('homepage.torrents.delete_selected', { count: selectedIds.size })
          }}
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
      <div v-else-if="torrents.length > 0" class="torrent-mobile-menu">
        <ab-menu :items="mobileOverflowActions" align="right">
          <template #trigger>
            <ab-icon-button :label="$t('common.moreActions')">
              <More :size="20" />
            </ab-icon-button>
          </template>
        </ab-menu>
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
      >
        <button
          type="button"
          class="torrent-select-button"
          :aria-pressed="selectedIds.has(torrent.id)"
          @click="toggleOne(torrent.id)"
        >
          <span
            class="torrent-checkbox"
            :class="{
              'torrent-checkbox--checked': selectedIds.has(torrent.id),
            }"
            aria-hidden="true"
          >
            <svg
              v-if="selectedIds.has(torrent.id)"
              viewBox="0 0 16 16"
              width="12"
              height="12"
            >
              <path
                d="M6.5 11.5L3 8l1-1 2.5 2.5L12 4l1 1z"
                fill="currentColor"
              />
            </svg>
          </span>
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
        </button>
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

    <Transition name="torrent-selection">
      <div
        v-if="isMobile && selectedIds.size > 0"
        class="torrent-selection-toolbar"
        role="toolbar"
        :aria-label="$t('common.select')"
      >
        <span class="torrent-selection-count">
          {{ selectedIds.size }} {{ $t('downloader.selected') }}
        </span>
        <ab-button size="sm" @click="toggleAll">
          {{
            allSelected
              ? $t('homepage.torrents.deselect_all')
              : $t('homepage.torrents.select_all')
          }}
        </ab-button>
        <ab-button size="sm" variant="danger" @click="handleDeleteSelected">
          {{
            $t('homepage.torrents.delete_selected', { count: selectedIds.size })
          }}
        </ab-button>
      </div>
    </Transition>
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
  padding: 0 8px 0 0;
  border-radius: var(--radius-sm);
  background: var(--color-surface-hover);
  transition: background-color var(--transition-fast);

  &:hover {
    background: color-mix(
      in srgb,
      var(--color-surface-hover) 80%,
      var(--color-primary)
    );
  }

  &--selected {
    background: color-mix(in srgb, var(--color-primary) 12%, transparent);
    outline: 1px solid var(--color-primary);
  }
}

.torrent-select-button {
  display: flex;
  min-width: 0;
  min-height: 44px;
  flex: 1;
  align-items: center;
  padding: 8px 4px 8px 12px;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: inherit;
  cursor: pointer;
  font: inherit;

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: -2px;
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
  text-align: left;
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

.torrent-selection-toolbar {
  display: none;
}

@media screen and (max-width: 639px) {
  .page-torrents {
    min-width: 0;
    max-width: 100%;
    overflow-x: hidden;
  }

  .toolbar {
    align-items: center;
    flex-wrap: nowrap;
    min-height: var(--touch-target);
    padding: 0 0 8px;
  }

  .toolbar-title {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .torrent-mobile-menu :deep(.ab-icon-btn) {
    width: var(--touch-target);
    height: var(--touch-target);
  }

  .torrent-scroll {
    max-width: 100%;
    padding: 0 0 8px;
    overflow-x: hidden;
  }

  .torrent-item {
    min-width: 0;
    min-height: 56px;
  }

  .torrent-select-button {
    min-height: 56px;
    padding-left: 8px;
  }

  .torrent-name {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    white-space: normal;
  }

  .torrent-delete {
    width: var(--touch-target);
    height: var(--touch-target);
    margin-left: 2px;
  }

  .torrent-selection-toolbar {
    position: sticky;
    bottom: 0;
    z-index: var(--z-sticky);
    display: flex;
    min-width: 0;
    min-height: 60px;
    align-items: center;
    gap: 6px;
    padding: 8px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    box-shadow: var(--shadow-md);
    color: var(--color-text-secondary);
    font-size: 12px;

    :deep(.ab-btn) {
      min-height: var(--touch-target);
    }
  }

  .torrent-selection-count {
    margin-right: auto;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  .torrent-selection-enter-active,
  .torrent-selection-leave-active {
    transition: opacity var(--transition-fast), transform var(--transition-fast);
  }

  .torrent-selection-enter-from,
  .torrent-selection-leave-to {
    opacity: 0;
    transform: translateY(8px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .torrent-selection-enter-active,
  .torrent-selection-leave-active {
    transition: none;
  }
}
</style>
