<script lang="tsx" setup>
import { type DataTableColumns, NDataTable } from 'naive-ui';
import AbProgress from '@/components/basic/ab-progress.vue';
import AbDownloaderMobileList from '@/components/downloader/ab-downloader-mobile-list.vue';
import { useConfirm } from '@/hooks/useConfirm';
import {
  formatTorrentEta,
  formatTorrentSize,
  formatTorrentSpeed,
  torrentStateLabel,
  torrentStateType,
} from '@/utils/downloader-display';
import type { QbTorrentInfo, TorrentGroup } from '#/downloader';

definePage({
  name: 'Downloader',
});

const { t } = useMyI18n();
const { config } = storeToRefs(useConfigStore());
const { getConfig } = useConfigStore();
const { groups, selectedHashes, loading } = storeToRefs(useDownloaderStore());
const {
  getAll,
  pauseSelected,
  resumeSelected,
  deleteSelected,
  toggleHash,
  toggleGroup,
  clearSelection,
} = useDownloaderStore();
const { confirm } = useConfirm();
const { isMobile } = useBreakpointQuery();

async function onDeleteSelected() {
  const ok = await confirm({
    title: t('downloader.action.delete'),
    body: t('downloader.action.delete_confirm'),
    confirmText: t('downloader.action.delete'),
    danger: true,
  });
  if (ok) deleteSelected(false);
}

const isNull = computed(() => {
  return config.value.downloader.host === '';
});

const { connected: sseConnected } = useEventStream();

const isActive = ref(false);
const { pause, resume } = useIntervalFn(
  () => {
    // SSE 已接管种子列表推送，或页面不可见时，跳过本次轮询请求。
    if (sseConnected.value || document.hidden) return;
    getAll();
  },
  5000,
  { immediate: false }
);

onActivated(async () => {
  isActive.value = true;
  await getConfig();
  if (isActive.value && !isNull.value) {
    getAll();
    resume();
  }
});

onDeactivated(() => {
  isActive.value = false;
  pause();
  clearSelection();
});

const tableColumnsValue = computed<DataTableColumns<QbTorrentInfo>>(() => [
  {
    type: 'selection',
  },
  {
    title: t('downloader.torrent.name'),
    key: 'name',
    ellipsis: { tooltip: true },
    minWidth: 200,
  },
  {
    title: t('downloader.torrent.progress'),
    key: 'progress',
    width: 160,
    render(row: QbTorrentInfo) {
      return (
        <AbProgress
          value={row.progress * 100}
          label={`${Math.round(row.progress * 100)}%`}
          state={
            row.state === 'error' || row.state === 'missingFiles'
              ? 'error'
              : 'active'
          }
        />
      );
    },
  },
  {
    title: t('downloader.torrent.status'),
    key: 'state',
    width: 100,
    render(row: QbTorrentInfo) {
      return (
        <ab-tag
          type={torrentStateType(row.state)}
          title={torrentStateLabel(row.state, t)}
        />
      );
    },
  },
  {
    title: t('downloader.torrent.size'),
    key: 'size',
    width: 100,
    render(row: QbTorrentInfo) {
      return formatTorrentSize(row.size);
    },
  },
  {
    title: t('downloader.torrent.dlspeed'),
    key: 'dlspeed',
    width: 110,
    render(row: QbTorrentInfo) {
      return formatTorrentSpeed(row.dlspeed);
    },
  },
  {
    title: t('downloader.torrent.upspeed'),
    key: 'upspeed',
    width: 110,
    render(row: QbTorrentInfo) {
      return formatTorrentSpeed(row.upspeed);
    },
  },
  {
    title: 'ETA',
    key: 'eta',
    width: 80,
    render(row: QbTorrentInfo) {
      return formatTorrentEta(row.eta);
    },
  },
  {
    title: t('downloader.torrent.peers'),
    key: 'peers',
    width: 110,
    render(row: QbTorrentInfo) {
      return `${row.num_seeds} / ${row.num_leechs}`;
    },
  },
]);

function tableRowKey(row: QbTorrentInfo) {
  return row.hash;
}

function onCheckedChange(group: TorrentGroup, keys: string[]) {
  const groupHashes = group.torrents.map((t) => t.hash);
  const otherSelected = selectedHashes.value.filter(
    (h) => !groupHashes.includes(h)
  );
  selectedHashes.value = [...otherSelected, ...keys];
}

function groupCheckedKeys(group: TorrentGroup): string[] {
  return group.torrents
    .filter((t) => selectedHashes.value.includes(t.hash))
    .map((t) => t.hash);
}
</script>

<template>
  <div class="page-downloader">
    <div v-if="isNull" class="empty-guide">
      <div class="empty-guide-header anim-fade-in">
        <div class="empty-guide-title">{{ $t('downloader.empty.title') }}</div>
        <div class="empty-guide-subtitle">
          {{ $t('downloader.empty.subtitle') }}
        </div>
      </div>

      <div class="empty-guide-steps">
        <div class="empty-guide-step anim-slide-up" style="--delay: 0.15s">
          <div class="empty-guide-step-number">1</div>
          <div class="empty-guide-step-content">
            <div class="empty-guide-step-title">
              {{ $t('downloader.empty.step1_title') }}
            </div>
            <div class="empty-guide-step-desc">
              {{ $t('downloader.empty.step1_desc') }}
            </div>
          </div>
        </div>

        <div class="empty-guide-step anim-slide-up" style="--delay: 0.3s">
          <div class="empty-guide-step-number">2</div>
          <div class="empty-guide-step-content">
            <div class="empty-guide-step-title">
              {{ $t('downloader.empty.step2_title') }}
            </div>
            <div class="empty-guide-step-desc">
              {{ $t('downloader.empty.step2_desc') }}
            </div>
          </div>
        </div>

        <div class="empty-guide-step anim-slide-up" style="--delay: 0.45s">
          <div class="empty-guide-step-number">3</div>
          <div class="empty-guide-step-content">
            <div class="empty-guide-step-title">
              {{ $t('downloader.empty.step3_title') }}
            </div>
            <div class="empty-guide-step-desc">
              {{ $t('downloader.empty.step3_desc') }}
            </div>
          </div>
        </div>
      </div>

      <RouterLink
        to="/config"
        class="empty-guide-action anim-slide-up"
        style="--delay: 0.6s"
      >
        {{ $t('sidebar.config') }}
      </RouterLink>
    </div>

    <div v-else class="downloader-content">
      <div v-if="groups.length === 0 && !loading" class="downloader-empty">
        {{ $t('downloader.empty_torrents') }}
      </div>

      <AbDownloaderMobileList
        v-if="isMobile"
        :groups="groups"
        :selected-hashes="selectedHashes"
        @toggle-hash="toggleHash"
        @toggle-group="toggleGroup"
      />

      <div v-else class="downloader-groups">
        <ab-fold-panel
          v-for="group in groups"
          :key="group.savePath"
          :title="`${group.name} (${group.count})`"
          :default-open="true"
        >
          <NDataTable
            :columns="tableColumnsValue"
            :data="group.torrents"
            :row-key="tableRowKey"
            :pagination="false"
            :bordered="false"
            :checked-row-keys="groupCheckedKeys(group)"
            size="small"
            @update:checked-row-keys="(keys: any) => onCheckedChange(group, keys as string[])"
          />
        </ab-fold-panel>
      </div>

      <Transition name="fade">
        <div v-if="selectedHashes.length > 0" class="action-bar">
          <span class="action-bar-count">
            {{ selectedHashes.length }} {{ $t('downloader.selected') }}
          </span>
          <div class="action-bar-buttons">
            <ab-button variant="primary" size="sm" @click="resumeSelected">{{
              $t('downloader.action.resume')
            }}</ab-button>
            <ab-button variant="secondary" size="sm" @click="pauseSelected">{{
              $t('downloader.action.pause')
            }}</ab-button>
            <ab-button variant="danger" size="sm" @click="onDeleteSelected">{{
              $t('downloader.action.delete')
            }}</ab-button>
          </div>
        </div>
      </Transition>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.page-downloader {
  overflow: auto;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}

.downloader-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 12px;
  padding-bottom: 60px;
}

.downloader-groups {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.downloader-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.action-bar {
  position: fixed;
  bottom: calc(24px + env(safe-area-inset-bottom, 0px));
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 20px;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  z-index: 100;
  max-width: calc(100vw - 32px);

  // Preserve the pre-existing <1024px toolbar layout for tablets.
  @media screen and (min-width: 640px) and (max-width: 1023px) {
    right: 16px;
    bottom: calc(72px + env(safe-area-inset-bottom, 0px));
    left: 16px;
    transform: none;
    flex-direction: column;
    gap: 8px;
    padding: 12px 16px;
  }

  @media screen and (max-width: 639px) {
    right: calc(var(--layout-padding) + env(safe-area-inset-right, 0px));
    left: calc(var(--layout-padding) + env(safe-area-inset-left, 0px));
    transform: none;
    display: grid;
    max-width: none;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    padding: 8px;
    bottom: calc(
      var(--layout-padding) + var(--layout-padding) + var(--nav-height) +
        env(safe-area-inset-bottom, 0px)
    );
  }
}

.action-bar-count {
  font-size: 13px;
  color: var(--color-text-secondary);
  white-space: nowrap;

  @media screen and (max-width: 639px) {
    grid-column: 1 / -1;
  }
}

.action-bar-buttons {
  display: flex;
  gap: 8px;

  @media screen and (min-width: 640px) and (max-width: 1023px) {
    width: 100%;

    :deep(.ab-btn) {
      flex: 1;
    }
  }

  @media screen and (max-width: 639px) {
    display: contents;
    width: 100%;

    :deep(.ab-btn) {
      min-width: 0;
      min-height: var(--touch-target);
      padding-inline: 6px;
      flex: 1;
    }
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(8px);
}

.empty-guide {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 24px;
}

.empty-guide-header {
  text-align: center;
  margin-bottom: 32px;
}

.empty-guide-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 6px;
}

.empty-guide-subtitle {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.empty-guide-steps {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 400px;
  width: 100%;
}

.empty-guide-step {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 14px 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  transition: background-color var(--transition-normal),
    border-color var(--transition-normal);
}

.empty-guide-step-number {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-guide-step-content {
  flex: 1;
  min-width: 0;
}

.empty-guide-step-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 4px;
}

.empty-guide-step-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.empty-guide-action {
  margin-top: 24px;
  padding: 8px 24px;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: background-color var(--transition-fast);

  &:hover {
    background: var(--color-primary-hover);
  }
}

.anim-fade-in {
  animation: fadeIn 0.5s ease both;
}

.anim-slide-up {
  animation: slideUp 0.45s cubic-bezier(0.16, 1, 0.3, 1) both;
  animation-delay: var(--delay, 0s);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media screen and (max-width: 639px) {
  .page-downloader,
  .downloader-content,
  .downloader-groups {
    min-width: 0;
    max-width: 100%;
    overflow-x: hidden;
  }

  .downloader-content {
    padding-bottom: 104px;
  }

  .fade-enter-from,
  .fade-leave-to {
    transform: translateY(8px);
  }

  .empty-guide {
    padding: 12px;
  }

  .empty-guide-header {
    margin-bottom: 20px;
  }

  .empty-guide-steps {
    gap: 10px;
  }

  .empty-guide-step {
    gap: 10px;
    padding: 12px;
  }

  .empty-guide-action {
    display: inline-flex;
    min-height: var(--touch-target);
    align-items: center;
    justify-content: center;
  }
}

@media (prefers-reduced-motion: reduce) {
  .fade-enter-active,
  .fade-leave-active {
    transition: none;
  }

  .anim-fade-in,
  .anim-slide-up {
    animation: none;
  }
}
</style>
