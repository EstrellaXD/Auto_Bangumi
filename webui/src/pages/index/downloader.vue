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

const { isMobile, isTablet } = useBreakpointQuery();

function progressCell(row: QbTorrentInfo) {
  return h(AbProgress, {
    value: row.progress * 100,
    label: `${Math.round(row.progress * 100)}%`,
    state:
      row.state === 'error' || row.state === 'missingFiles' ? 'error' : 'active',
  });
}

function stateCell(row: QbTorrentInfo) {
  return h(AbTag, { type: stateType(row.state), title: stateLabel(row.state) });
}

// 数据列：等宽数字右对齐，小数点与单位上下对齐
const numCol = { align: 'right', className: 'num-col' } as const;

// 手机只留勾选与名称列，进度/状态/大小收进名称下方一行
function mobileNameCell(row: QbTorrentInfo) {
  return h('div', { class: 'torrent-cell' }, [
    h('div', { class: 'torrent-name' }, row.name),
    h('div', { class: 'torrent-meta' }, [
      progressCell(row),
      stateCell(row),
      h('span', { class: 'num-col' }, formatSize(row.size)),
      downloaders.multiple.value
        ? h('span', { class: 'num-col torrent-instance' }, row.downloader_id)
        : null,
    ]),
  ]);
}

const tableColumnsValue = computed<DataTableColumns<Row>>(() => {
  const nameCol: DataTableColumns<Row>[number] = {
    title: t('downloader.torrent.name'),
    key: 'name',
    // CSS 省略号 + title：不用逐行测量宽度的 tooltip
    ellipsis: !isMobile.value,
    className: 'name-col',
    minWidth: 200,
    colSpan: (row: Row): number =>
      isGroupRow(row) ? tableColumnsValue.value.length - 1 : 1,
    cellProps: (row) => ({
      title: isGroupRow(row) ? row.group.savePath : row.name,
    }),
    render: (row) => {
      if (!isGroupRow(row)) return isMobile.value ? mobileNameCell(row) : row.name;
      const label = `${row.group.name} (${row.group.count})`;
      // 手机关掉了列省略号，分组名自己截断
      return isMobile.value
        ? h('span', { class: 'torrent-cell' }, h('span', { class: 'torrent-name' }, label))
        : label;
    },
  };
  if (isMobile.value) return [{ type: 'selection' }, nameCol];

  return [
    { type: 'selection' },
    nameCol,
    {
      title: t('downloader.torrent.progress'),
      key: 'progress',
      width: 140,
      render: torrentCell(progressCell),
    },
    {
      title: t('downloader.torrent.status'),
      key: 'state',
      width: 130,
      render: torrentCell(stateCell),
    },
    {
      title: t('downloader.torrent.size'),
      key: 'size',
      width: 100,
      ...numCol,
      render: torrentCell((row) => formatSize(row.size)),
    },
    {
      title: t('downloader.torrent.dlspeed'),
      key: 'dlspeed',
      width: 110,
      ...numCol,
      render: torrentCell((row) => formatSpeed(row.dlspeed)),
    },
    // 平板宽度不够：去掉上传速度、ETA、做种/下载
    ...(isTablet.value
      ? []
      : [
          {
            title: t('downloader.torrent.upspeed'),
            key: 'upspeed',
            width: 110,
            ...numCol,
            render: torrentCell((row) => formatSpeed(row.upspeed)),
          },
          {
            title: 'ETA',
            key: 'eta',
            width: 72,
            ...numCol,
            render: torrentCell((row) => formatEta(row.eta)),
          },
          {
            title: t('downloader.torrent.peers'),
            key: 'peers',
            width: 110,
            ...numCol,
            render: torrentCell((row) => `${row.num_seeds} / ${row.num_leechs}`),
          },
        ]),
    // 多个下载器实例时放在最后；定宽，名称列是唯一的弹性列
    ...(downloaders.multiple.value
      ? [
          {
            title: t('downloader.torrent.instance'),
            key: 'downloader_id',
            width: 130,
            ellipsis: true,
            cellProps: (row: Row) => ({
              title: isGroupRow(row) ? undefined : row.downloader_id,
            }),
          },
        ]
      : []),
  ];
});

// 表格最小宽度 = 各列定宽 + 名称列下限：WebKit 在 table-layout: fixed 下忽略
// <col> 的 min-width，不设 scroll-x 时名称列会被算成 0
const tableMinWidth = computed(() =>
  tableColumnsValue.value.reduce((sum, col) => {
    if (col.type === 'selection') return sum + 40;
    const c = col as { width?: number; minWidth?: number };
    return sum + (c.width ?? c.minWidth ?? 0);
  }, 0)
);
</script>

<template>
  <div class="page-downloader">
    <div v-if="isNull" class="page-empty">
      <ab-empty
        :title="$t('downloader.empty.title')"
        :description="$t('downloader.empty.subtitle')"
      >
        <template #action>
          <ol class="empty-steps">
            <li v-for="n in 3" :key="n">
              <span class="empty-steps-title">{{
                $t(`downloader.empty.step${n}_title`)
              }}</span>
              {{ $t(`downloader.empty.step${n}_desc`) }}
            </li>
          </ol>
          <ab-button variant="primary" @click="$router.push('/config')">
            {{ $t('sidebar.config') }}
          </ab-button>
        </template>
      </ab-empty>
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
        :scroll-x="tableMinWidth"
        virtual-scroll
        flex-height
        size="small"
        @update:checked-row-keys="onCheckedChange"
        @update:expanded-row-keys="onExpandedChange"
      />

      <!-- 操作栏在内容列底部占位（不 fixed）：不遮表格、不压底栏，无需预留 padding -->
      <Transition name="action-bar">
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

  :deep(.num-col) {
    white-space: nowrap;
  }

  // 列 className 同时加在 th 上：只给单元格用等宽字体，表头与其他列一致
  :deep(td.num-col),
  :deep(.torrent-meta .num-col) {
    font-family: var(--font-mono);
    font-size: 13px;
    font-variant-numeric: tabular-nums;
  }

  // 手机名称格：名称一行省略，下方一行进度/状态/大小
  :deep(.torrent-cell) {
    display: inline-flex;
    flex-direction: column;
    gap: 4px;
    width: calc(100% - 40px);
    vertical-align: top;
  }

  :deep(.torrent-name) {
    overflow: hidden;
    text-overflow: ellipsis;
  }

  // 进度条定宽：各行轨道等长、状态标签起点对齐；大小靠右，格子太窄时换到下一行
  :deep(.torrent-meta) {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px 8px;
    font-size: 12px;
    color: var(--color-text-secondary);

    .ab-progress {
      flex: 0 0 80px;
    }

    > .num-col {
      margin-left: auto;
    }

    // 多实例时实例 id 独占一行，过长省略
    > .torrent-instance {
      flex-basis: 100%;
      min-width: 0;
      margin-left: 0;
      overflow: hidden;
      text-overflow: ellipsis;
    }
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
  flex-shrink: 0;
  align-self: center;
  display: flex;
  align-items: center;
  gap: 16px;
  max-width: 100%;
  padding: 10px 20px;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-md);

  @media (width < 640px) {
    align-self: stretch;
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

  @media (width < 640px) {
    width: 100%;

    :deep(.ab-btn) {
      flex: 1;
    }
  }
}

.action-bar-enter-active,
.action-bar-leave-active {
  transition: opacity var(--transition-normal),
    transform var(--transition-normal);
}

.action-bar-enter-from,
.action-bar-leave-to {
  opacity: 0;
  transform: translateY(4px);
}
</style>
