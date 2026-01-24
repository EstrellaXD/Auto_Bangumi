<script lang="tsx" setup>
import { NDataTable, NProgress, type DataTableColumns } from 'naive-ui';
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

const isNull = computed(() => {
  return config.value.downloader.host === '';
});

let timer: ReturnType<typeof setInterval> | null = null;

onActivated(() => {
  getConfig();
  if (!isNull.value) {
    getAll();
    timer = setInterval(getAll, 5000);
  }
});

onDeactivated(() => {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
  clearSelection();
});

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i];
}

function formatSpeed(bytesPerSec: number): string {
  if (bytesPerSec === 0) return '-';
  return formatSize(bytesPerSec) + '/s';
}

function formatEta(seconds: number): string {
  if (seconds <= 0 || seconds === 8640000) return '-';
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h${m}m`;
}

function stateLabel(state: string): string {
  const map: Record<string, string> = {
    downloading: t('downloader.state.downloading'),
    uploading: t('downloader.state.seeding'),
    pausedDL: t('downloader.state.paused'),
    pausedUP: t('downloader.state.paused'),
    stalledDL: t('downloader.state.stalled'),
    stalledUP: t('downloader.state.seeding'),
    queuedDL: t('downloader.state.queued'),
    queuedUP: t('downloader.state.queued'),
    checkingDL: t('downloader.state.checking'),
    checkingUP: t('downloader.state.checking'),
    error: t('downloader.state.error'),
    missingFiles: t('downloader.state.error'),
    metaDL: t('downloader.state.metadata'),
  };
  return map[state] || state;
}

function stateType(state: string): string {
  if (state.includes('paused')) return 'inactive';
  if (state === 'downloading' || state === 'forcedDL') return 'active';
  if (state.includes('UP') || state === 'uploading') return 'primary';
  if (state === 'error' || state === 'missingFiles') return 'warn';
  return 'primary';
}

function isGroupAllSelected(group: TorrentGroup): boolean {
  return group.torrents.every((t) => selectedHashes.value.includes(t.hash));
}

function tableColumns(): DataTableColumns<QbTorrentInfo> {
  return [
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
          <NProgress
            type="line"
            percentage={Math.round(row.progress * 100)}
            indicator-placement="inside"
            processing={row.state === 'downloading' || row.state === 'forcedDL'}
          />
        );
      },
    },
    {
      title: t('downloader.torrent.status'),
      key: 'state',
      width: 100,
      render(row: QbTorrentInfo) {
        return <ab-tag type={stateType(row.state)} title={stateLabel(row.state)} />;
      },
    },
    {
      title: t('downloader.torrent.size'),
      key: 'size',
      width: 100,
      render(row: QbTorrentInfo) {
        return formatSize(row.size);
      },
    },
    {
      title: t('downloader.torrent.dlspeed'),
      key: 'dlspeed',
      width: 110,
      render(row: QbTorrentInfo) {
        return formatSpeed(row.dlspeed);
      },
    },
    {
      title: t('downloader.torrent.upspeed'),
      key: 'upspeed',
      width: 110,
      render(row: QbTorrentInfo) {
        return formatSpeed(row.upspeed);
      },
    },
    {
      title: 'ETA',
      key: 'eta',
      width: 80,
      render(row: QbTorrentInfo) {
        return formatEta(row.eta);
      },
    },
    {
      title: t('downloader.torrent.peers'),
      key: 'peers',
      width: 90,
      render(row: QbTorrentInfo) {
        return `${row.num_seeds} / ${row.num_leechs}`;
      },
    },
  ];
}

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
        <div class="empty-guide-subtitle">{{ $t('downloader.empty.subtitle') }}</div>
      </div>

      <div class="empty-guide-steps">
        <div class="empty-guide-step anim-slide-up" style="--delay: 0.15s">
          <div class="empty-guide-step-number">1</div>
          <div class="empty-guide-step-content">
            <div class="empty-guide-step-title">{{ $t('downloader.empty.step1_title') }}</div>
            <div class="empty-guide-step-desc">{{ $t('downloader.empty.step1_desc') }}</div>
          </div>
        </div>

        <div class="empty-guide-step anim-slide-up" style="--delay: 0.3s">
          <div class="empty-guide-step-number">2</div>
          <div class="empty-guide-step-content">
            <div class="empty-guide-step-title">{{ $t('downloader.empty.step2_title') }}</div>
            <div class="empty-guide-step-desc">{{ $t('downloader.empty.step2_desc') }}</div>
          </div>
        </div>

        <div class="empty-guide-step anim-slide-up" style="--delay: 0.45s">
          <div class="empty-guide-step-number">3</div>
          <div class="empty-guide-step-content">
            <div class="empty-guide-step-title">{{ $t('downloader.empty.step3_title') }}</div>
            <div class="empty-guide-step-desc">{{ $t('downloader.empty.step3_desc') }}</div>
          </div>
        </div>
      </div>

      <RouterLink to="/config" class="empty-guide-action anim-slide-up" style="--delay: 0.6s">
        {{ $t('sidebar.config') }}
      </RouterLink>
    </div>

    <div v-else class="downloader-content">
      <div v-if="groups.length === 0 && !loading" class="downloader-empty">
        {{ $t('downloader.empty_torrents') }}
      </div>

      <div v-else class="downloader-groups">
        <ab-fold-panel
          v-for="group in groups"
          :key="group.savePath"
          :title="`${group.name} (${group.count})`"
          :default-open="true"
        >
          <NDataTable
            :columns="tableColumns()"
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
            <ab-button @click="resumeSelected">{{ $t('downloader.action.resume') }}</ab-button>
            <ab-button @click="pauseSelected">{{ $t('downloader.action.pause') }}</ab-button>
            <ab-button type="warn" @click="deleteSelected(false)">{{ $t('downloader.action.delete') }}</ab-button>
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

  @include forMobile {
    bottom: calc(72px + env(safe-area-inset-bottom, 0px));
    left: 16px;
    right: 16px;
    transform: none;
    flex-direction: column;
    gap: 8px;
    padding: 12px 16px;
  }
}

.action-bar-count {
  font-size: 13px;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.action-bar-buttons {
  display: flex;
  gap: 8px;

  @include forMobile {
    width: 100%;

    :deep(.btn) {
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
</style>
