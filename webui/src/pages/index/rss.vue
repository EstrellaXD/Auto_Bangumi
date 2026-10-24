<script lang="ts" setup>
import { RefreshCw } from '@lucide/vue';
import { type DataTableColumns, NDataTable } from 'naive-ui';
import AbButton from '@/components/basic/ab-button.vue';
import AbEmpty from '@/components/basic/ab-empty.vue';
import AbTag from '@/components/basic/ab-tag.vue';
import AbTooltip from '@/components/basic/ab-tooltip.vue';
import { useConfirm } from '@/hooks/useConfirm';
import type { RSS } from '#/rss';

definePage({
  name: 'RSS',
});

const { t } = useMyI18n();
const { confirm } = useConfirm();

const { isMobile } = useBreakpointQuery();
const { rss, selectedRSS, isRefreshingAll, isLoading } = storeToRefs(
  useRSSStore()
);
const {
  getAll,
  deleteSelected,
  disableSelected,
  enableSelected,
  refreshRSS,
  refreshAllRSS,
} = useRSSStore();

async function onDeleteSelected() {
  const ok = await confirm({
    title: t('rss.delete'),
    body: t('rss.delete_confirm'),
    confirmText: t('rss.delete'),
    danger: true,
  });
  if (ok) deleteSelected();
}

onActivated(() => {
  getAll();
});

// Tracks which single row is refreshing so only its button spins — the
// store's isRefreshingAll only covers the "refresh all" button.
const refreshingId = ref<number | null>(null);
const refreshFailedId = ref<number | null>(null);

async function onRefreshOne(id: number) {
  refreshingId.value = id;
  try {
    const result = await refreshRSS(id);
    refreshFailedId.value = result.ok ? null : id;
  } finally {
    refreshingId.value = null;
  }
}

const rssColumns = computed<DataTableColumns<RSS>>(() => [
  {
    type: 'selection',
  },
  {
    // 名称列同时承载来源元信息（解析器 / 聚合），Status 列只保留运行状态
    title: t('rss.name'),
    key: 'name',
    render(rss: RSS) {
      return h('div', { class: 'rss-name-cell' }, [
        h('span', { class: 'rss-name', title: rss.name }, rss.name),
        rss.parser && h(AbTag, { type: 'info', title: rss.parser }),
        rss.aggregate && h(AbTag, { type: 'info', title: t('rss.aggregate') }),
      ]);
    },
  },
  {
    title: t('rss.url'),
    key: 'url',
    minWidth: 240,
    ellipsis: {
      tooltip: true,
    },
  },
  {
    title: t('rss.status'),
    key: 'status',
    align: 'right',
    minWidth: 140,
    render(rss: RSS) {
      return h('div', { class: 'flex justify-end gap-x-8' }, [
        rss.connection_status === 'healthy' &&
        h(AbTag, { type: 'success', title: t('rss.connected') }),
        rss.connection_status === 'error' &&
        h(
          AbTooltip,
          { content: rss.last_error || t('rss.error') },
          () => h(AbTag, { type: 'danger', title: t('rss.error') })
        ),
        rss.enabled
          ? h(AbTag, { type: 'success', title: t('rss.active') })
          : h(AbTag, { type: 'neutral', title: t('rss.inactive') }),
      ]);
    },
  },
  {
    title: t('rss.refresh'),
    key: 'actions',
    align: 'center',
    width: 90,
    render(rss: RSS) {
      const isRowRefreshing = refreshingId.value === rss.id;
      const isRowFailed = refreshFailedId.value === rss.id;
      return h(
        AbButton,
        {
          size: 'sm',
          variant: isRowFailed ? 'danger' : 'secondary',
          title: t('rss.refresh'),
          disabled: isRowRefreshing,
          onClick: () => onRefreshOne(rss.id),
        },
        () =>
          h(RefreshCw, {
            size: 14,
            class: isRowRefreshing ? 'animate-spin' : undefined,
          })
      );
    },
  },
]);

const rssRowKey = (row: RSS) => row.id;

function onSelectedRSSUpdate(keys: unknown[]) {
  selectedRSS.value = keys as number[];
}
</script>

<template>
  <div class="page-rss">
    <ab-container :title="$t('rss.title')">
      <template #title-right>
        <AbButton
          size="sm"
          :title="$t('rss.refresh_all')"
          :disabled="isRefreshingAll"
          @click="refreshAllRSS"
        >
          <template #icon>
            <RefreshCw :size="14" :class="{ 'animate-spin': isRefreshingAll }" />
          </template>
          {{ $t('rss.refresh_all') }}
        </AbButton>
      </template>

      <!-- Mobile: Card-based list -->
      <ab-list
        v-if="isMobile"
        :items="rss || []"
        selectable
        key-field="id"
        :loading="isLoading && rss.length === 0"
        :selected="selectedRSS"
        @update:selected="onSelectedRSSUpdate"
      >
        <template #row="{ item }">
          <div class="rss-card-content">
            <div class="rss-card-header">
              <div class="rss-card-name">
                {{ item.name }}
              </div>
              <AbButton
                size="sm"
                :variant="refreshFailedId === item.id ? 'danger' : 'secondary'"
                :title="$t('rss.refresh')"
                :aria-label="$t('rss.refresh')"
                :disabled="refreshingId === item.id"
                @click.stop="onRefreshOne(item.id)"
              >
                <RefreshCw :size="14" :class="{ 'animate-spin': refreshingId === item.id }" />
              </AbButton>
            </div>
            <div class="rss-card-url">
              {{ item.url }}
            </div>
            <div class="rss-card-tags">
              <AbTag v-if="item.parser" type="info" :title="item.parser" />
              <AbTag v-if="item.aggregate" type="info" :title="$t('rss.aggregate')" />
              <AbTag
                v-if="item.connection_status === 'healthy'"
                type="success"
                :title="$t('rss.connected')"
              />
              <AbTag
                v-if="item.connection_status === 'error'"
                type="danger"
                :title="$t('rss.error')"
              />
              <AbTag
                :type="item.enabled ? 'success' : 'neutral'"
                :title="item.enabled ? $t('rss.active') : $t('rss.inactive')"
              />
            </div>
            <!-- Inline on touch — a tooltip can't be hovered on a phone -->
            <div
              v-if="item.connection_status === 'error' && item.last_error"
              class="rss-card-error"
            >
              {{ item.last_error }}
            </div>
          </div>
        </template>
      </ab-list>

      <!-- Desktop: Data table -->
      <NDataTable
        v-else
        :columns="rssColumns"
        :data="rss"
        :row-key="rssRowKey"
        :loading="isLoading && rss.length === 0"
        :pagination="false"
        :bordered="false"
        :max-height="500"
        @update:checked-row-keys="onSelectedRSSUpdate"
      >
        <template #empty>
          <AbEmpty :title="$t('common.empty')" />
        </template>
      </NDataTable>
    </ab-container>

    <!-- 操作栏在卡片下方占位，长列表时 sticky 贴在滚动区底部；样式与下载器页一致 -->
    <Transition name="action-bar">
      <div v-if="selectedRSS.length > 0" class="action-bar">
        <span class="action-bar-count">
          {{ selectedRSS.length }} {{ $t('downloader.selected') }}
        </span>
        <div class="action-bar-buttons">
          <AbButton variant="primary" size="sm" @click="enableSelected">
            {{ $t('rss.enable') }}
          </AbButton>
          <AbButton variant="secondary" size="sm" @click="disableSelected">
            {{ $t('rss.disable') }}
          </AbButton>
          <AbButton variant="danger" size="sm" @click="onDeleteSelected">
            {{ $t('rss.delete') }}
          </AbButton>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style lang="scss" scoped>
.page-rss {
  overflow: auto;
  flex-grow: 1;
}

:deep(.rss-name-cell) {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  row-gap: 4px;
  min-width: 0;

  .rss-name {
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

// naive 的空状态容器居中内容；ab-empty 是左对齐说明，铺满表格宽度
:deep(.n-data-table-empty .ab-empty) {
  width: 100%;
}

// 与 downloader.vue 的 .action-bar 同一套样式；在 .page-rss 滚动区内 sticky，
// 按内容区居中，手机上与卡片同宽，不压底栏
.action-bar {
  position: sticky;
  bottom: 0;
  z-index: var(--z-fixed);
  display: flex;
  align-items: center;
  gap: 16px;
  width: fit-content;
  max-width: 100%;
  margin: 12px auto 0;
  padding: 10px 20px;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-md);

  @media (width < 640px) {
    width: auto;
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
  transition: opacity var(--transition-normal), transform var(--transition-normal);
}

.action-bar-enter-from,
.action-bar-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

// Mobile RSS card styles
// 复选框与名称行顶部对齐，不随卡片高度垂直居中
:deep(.ab-list-row) {
  align-items: flex-start;
}

:deep(.ab-list-check) {
  // 名称行高度 = 刷新按钮高度（桌面 28px，触屏 44px），复选框 16px，居中到该行；
  // ab-list 用 6px 内边距 + -6px 外边距扩大命中区，这里的值已扣掉那 6px
  margin-top: 0;

  @include forTouch {
    margin-top: 8px;
  }
}

.rss-card-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rss-card-header {
  display: flex;
  align-items: center;
  gap: 8px;

  // 按钮与卡片同为 surface-2，换成 surface 底色才能看出按钮边界
  :deep(.ab-btn--secondary) {
    flex-shrink: 0;
    background: var(--color-surface);
  }
}

.rss-card-name {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rss-card-url {
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rss-card-error {
  font-size: 12px;
  color: var(--color-danger);
  word-break: break-word;
}

.rss-card-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-top: 4px;
}
</style>
