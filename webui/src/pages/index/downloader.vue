<script lang="ts" setup>
import type { VNodeChild } from 'vue';
import {
  type DataTableColumns,
  type DataTableRowKey,
  NDataTable,
} from 'naive-ui';
import AbProgress from '@/components/basic/ab-progress.vue';
import AbTag from '@/components/basic/ab-tag.vue';
import { useConfirm } from '@/hooks/useConfirm';
import type { QbTorrentInfo, TorrentGroup } from '#/downloader';
import { useDownloaderInstances } from '@/hooks/useDownloaderInstances';
import { hasConfiguredDownloader, torrentKey } from '@/store/downloader';

definePage({
  name: 'Downloader',
});

const { t } = useMyI18n();
const { config } = storeToRefs(useConfigStore());
const { getConfig } = useConfigStore();
const { groups, selectedKeys, loading } = storeToRefs(useDownloaderStore());
const {
  getAll,
  pauseSelected,
  resumeSelected,
  deleteSelected,
  clearSelection,
} = useDownloaderStore();
const { confirm } = useConfirm();

async function onDeleteSelected() {
  const ok = await confirm({
    title: t('downloader.action.delete'),
    body: t('downloader.action.delete_confirm'),
    confirmText: t('downloader.action.delete'),
    danger: true,
  });
  if (ok) deleteSelected(false);
}

const isNull = computed(
  () => !hasConfiguredDownloader(config.value.plugins.instances)
);

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

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / 1024 ** i).toFixed(1)} ${units[i]}`;
}

function formatSpeed(bytesPerSec: number): string {
  if (bytesPerSec === 0) return '-';
  return `${formatSize(bytesPerSec)}/s`;
}

function formatEta(seconds: number): string {
  if (seconds <= 0 || seconds === 8640000) return '-';
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  // 不能叫 h：unimport 按名字判断，模块里出现 `const h` 就不再自动导入 vue 的 h()
  const hours = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${hours}h${m}m`;
}

function stateLabel(state: string): string {
  const map: Record<string, string> = {
    downloading: t('downloader.state.downloading'),
    uploading: t('downloader.state.seeding'),
    pausedDL: t('downloader.state.paused'),
    pausedUP: t('downloader.state.paused'),
    // qBittorrent 5.0+ 把 paused* 状态改名为 stopped*
    stoppedDL: t('downloader.state.paused'),
    stoppedUP: t('downloader.state.paused'),
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

function stateType(state: string): 'neutral' | 'success' | 'info' | 'danger' {
  if (state.includes('paused') || state.includes('stopped')) return 'neutral';
  if (state === 'downloading' || state === 'forcedDL') return 'success';
  if (state.includes('UP') || state === 'uploading') return 'info';
  if (state === 'error' || state === 'missingFiles') return 'danger';
  return 'info';
}

/** 分组头行：同一个虚拟表里以树形父行显示，children 为该组的种子 */
interface GroupRow {
  key: string;
  group: TorrentGroup;
  children: QbTorrentInfo[];
}
type Row = QbTorrentInfo | GroupRow;

function isGroupRow(row: Row): row is GroupRow {
  return 'group' in row;
}

function rowKey(row: Row): string {
  return isGroupRow(row) ? row.key : torrentKey(row);
}

function rowClassName(row: Row): string {
  return isGroupRow(row) ? 'group-row' : '';
}

/** 分组头行的名称格跨满其余列，种子列的渲染只处理种子行 */
function torrentCell(render: (row: QbTorrentInfo) => VNodeChild) {
  return (row: Row) => (isGroupRow(row) ? null : render(row));
}

const rows = computed<GroupRow[]>(() =>
  groups.value.map((group) => ({
    key: `group:${group.savePath}`,
    group,
    children: group.torrents,
  }))
);

// 记录折叠的分组，新出现的分组默认展开
const collapsed = shallowRef(new Set<string>());
const expandedKeys = computed(() =>
  rows.value.filter((r) => !collapsed.value.has(r.key)).map((r) => r.key)
);

function onExpandedChange(keys: DataTableRowKey[]) {
  const open = new Set(keys);
  collapsed.value = new Set(
    rows.value.map((r) => r.key).filter((k) => !open.has(k))
  );
}

const checkedKeys = computed(() => [...selectedKeys.value]);

// 级联勾选会带上分组头的键，只保留种子键
function onCheckedChange(keys: DataTableRowKey[]) {
  const groupKeys = new Set(rows.value.map((r) => r.key));
  selectedKeys.value = new Set(
    keys.filter((k) => !groupKeys.has(k as string)) as string[]
  );
}

// 多个下载器实例时标出每个种子所在的实例
const downloaders = useDownloaderInstances();

const tableColumnsValue = computed<DataTableColumns<Row>>(() => [
  {
    type: 'selection',
  },
  {
    title: t('downloader.torrent.name'),
    key: 'name',
    // CSS 省略号 + title：不用逐行测量宽度的 tooltip
    ellipsis: true,
    className: 'name-col',
    minWidth: 200,
    colSpan: (row: Row): number =>
      isGroupRow(row) ? tableColumnsValue.value.length - 1 : 1,
    cellProps: (row) => ({
      title: isGroupRow(row) ? row.group.savePath : row.name,
    }),
    render: (row) =>
      isGroupRow(row) ? `${row.group.name} (${row.group.count})` : row.name,
  },
  {
    title: t('downloader.torrent.progress'),
    key: 'progress',
    width: 160,
    render: torrentCell((row) => {
      return h(AbProgress, {
        value: row.progress * 100,
        label: `${Math.round(row.progress * 100)}%`,
        state:
          row.state === 'error' || row.state === 'missingFiles'
            ? 'error'
            : 'active',
      });
    }),
  },
  {
    title: t('downloader.torrent.status'),
    key: 'state',
    width: 100,
    render: torrentCell((row) => {
      return h(AbTag, {
        type: stateType(row.state),
        title: stateLabel(row.state),
      });
    }),
  },
  {
    title: t('downloader.torrent.size'),
    key: 'size',
    width: 100,
    render: torrentCell((row) => {
      return formatSize(row.size);
    }),
  },
  {
    title: t('downloader.torrent.dlspeed'),
    key: 'dlspeed',
    width: 110,
    render: torrentCell((row) => {
      return formatSpeed(row.dlspeed);
    }),
  },
  {
    title: t('downloader.torrent.upspeed'),
    key: 'upspeed',
    width: 110,
    render: torrentCell((row) => {
      return formatSpeed(row.upspeed);
    }),
  },
  {
    title: 'ETA',
    key: 'eta',
    width: 80,
    render: torrentCell((row) => {
      return formatEta(row.eta);
    }),
  },
  {
    title: t('downloader.torrent.peers'),
    key: 'peers',
    width: 110,
    render: torrentCell((row) => {
      return `${row.num_seeds} / ${row.num_leechs}`;
    }),
  },
  // 放在最后并完整显示 id（触屏没有悬停提示）
  ...(downloaders.multiple.value
    ? [
        {
          title: t('downloader.torrent.instance'),
          key: 'downloader_id',
          minWidth: 110,
        },
      ]
    : []),
]);
</script>

<template>
  <div class="page-downloader">
    <div v-if="isNull" class="empty-guide">
      <div class="empty-guide-header anim-fade-in">
        <div class="empty-guide-title">
          {{ $t('downloader.empty.title') }}
        </div>
        <div class="empty-guide-subtitle">
          {{ $t('downloader.empty.subtitle') }}
        </div>
      </div>

      <div class="empty-guide-steps">
        <div class="empty-guide-step anim-slide-up" style="--delay: 0.15s">
          <div class="empty-guide-step-number">
            1
          </div>
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
          <div class="empty-guide-step-number">
            2
          </div>
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
          <div class="empty-guide-step-number">
            3
          </div>
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

      <!-- 单个虚拟滚动表：只渲染可见行；不放进 NCollapseItem，SSE 数据才能刷新行 -->
      <NDataTable
        v-else
        class="downloader-table"
        :columns="tableColumnsValue"
        :data="rows"
        :row-key="rowKey"
        :row-class-name="rowClassName"
        :pagination="false"
        :bordered="false"
        :checked-row-keys="checkedKeys"
        :expanded-row-keys="expandedKeys"
        virtual-scroll
        flex-height
        size="small"
        @update:checked-row-keys="onCheckedChange"
        @update:expanded-row-keys="onExpandedChange"
      />

      <Transition name="fade">
        <div v-if="selectedKeys.size > 0" class="action-bar">
          <span class="action-bar-count">
            {{ selectedKeys.size }} {{ $t('downloader.selected') }}
          </span>
          <div class="action-bar-buttons">
            <ab-button variant="primary" size="sm" @click="resumeSelected">
              {{
                $t('downloader.action.resume')
              }}
            </ab-button>
            <ab-button variant="secondary" size="sm" @click="pauseSelected">
              {{
                $t('downloader.action.pause')
              }}
            </ab-button>
            <ab-button variant="danger" size="sm" @click="onDeleteSelected">
              {{
                $t('downloader.action.delete')
              }}
            </ab-button>
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
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.downloader-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  gap: 12px;
  padding-bottom: 60px;
}

// flex-height：表格填满页面剩余高度，虚拟滚动在表体内进行
.downloader-table {
  flex: 1;
  min-height: 0;

  :deep(.group-row .n-data-table-td) {
    font-weight: 600;
  }

  // 树形缩进与展开按钮占 40px，名称不换行到下一行
  :deep(.name-col) {
    white-space: nowrap;
  }

  :deep(.name-col .n-data-table-td__ellipsis) {
    max-width: calc(100% - 40px);
  }
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

    :deep(.ab-btn) {
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
