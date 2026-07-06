<script lang="tsx" setup>
import { type DataTableColumns, NDataTable, NTooltip } from 'naive-ui';
import AbButton from '@/components/basic/ab-button.vue';
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
    className: 'text-h3',
    render(rss: RSS) {
      return (
        <div class="rss-name-cell">
          <span class="rss-name" title={rss.name}>
            {rss.name}
          </span>
          {rss.parser && <ab-tag type="info" title={rss.parser} />}
          {rss.aggregate && <ab-tag type="info" title={t('rss.aggregate')} />}
        </div>
      );
    },
  },
  {
    title: t('rss.url'),
    key: 'url',
    className: 'text-h3',
    minWidth: 400,
    ellipsis: {
      tooltip: true,
    },
  },
  {
    title: t('rss.status'),
    key: 'status',
    className: 'text-h3',
    align: 'right',
    minWidth: 140,
    render(rss: RSS) {
      return (
        <div flex="~ justify-end gap-x-8">
          {rss.connection_status === 'healthy' && (
            <ab-tag type="success" title={t('rss.connected')} />
          )}
          {rss.connection_status === 'error' && (
            <NTooltip>
              {{
                trigger: () => <ab-tag type="danger" title={t('rss.error')} />,
                default: () => rss.last_error || 'Unknown error',
              }}
            </NTooltip>
          )}
          {rss.enabled ? (
            <ab-tag type="success" title={t('rss.active')} />
          ) : (
            <ab-tag type="neutral" title={t('rss.inactive')} />
          )}
        </div>
      );
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
      return (
        <AbButton
          size="sm"
          variant={isRowFailed ? 'danger' : 'secondary'}
          {...{ title: t('rss.refresh') }}
          disabled={isRowRefreshing}
          onClick={() => onRefreshOne(rss.id)}
        >
          <div
            class={
              isRowRefreshing ? 'i-carbon-renew animate-spin' : 'i-carbon-renew'
            }
          />
        </AbButton>
      );
    },
  },
]);

const rssRowKey = (row: RSS) => row.id;
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
            <div
              :class="
                isRefreshingAll
                  ? 'i-carbon-renew animate-spin'
                  : 'i-carbon-renew'
              "
            ></div>
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
        @update:selected="(keys) => (selectedRSS = keys as number[])"
      >
        <template #row="{ item }">
          <div class="rss-card-content">
            <div class="rss-card-name">{{ item.name }}</div>
            <div class="rss-card-url">{{ item.url }}</div>
            <div class="rss-card-tags">
              <ab-tag v-if="item.parser" type="info" :title="item.parser" />
              <ab-tag v-if="item.aggregate" type="info" title="aggregate" />
              <ab-tag
                v-if="item.connection_status === 'healthy'"
                type="success"
                :title="$t('rss.connected')"
              />
              <ab-tag
                v-if="item.connection_status === 'error'"
                type="danger"
                :title="$t('rss.error')"
              />
              <ab-tag
                :type="item.enabled ? 'success' : 'neutral'"
                :title="
                  item.enabled
                    ? $t('config.notification_set.enabled')
                    : $t('config.notification_set.disabled')
                "
              />
            </div>
            <!-- Inline on touch — a tooltip can't be hovered on a phone -->
            <div
              v-if="item.connection_status === 'error' && item.last_error"
              class="rss-card-error"
            >
              {{ item.last_error }}
            </div>
            <div class="rss-card-actions" @click.stop>
              <AbButton
                size="sm"
                :variant="refreshFailedId === item.id ? 'danger' : 'secondary'"
                :title="$t('rss.refresh')"
                :disabled="refreshingId === item.id"
                @click="onRefreshOne(item.id)"
              >
                <div
                  :class="
                    refreshingId === item.id
                      ? 'i-carbon-renew animate-spin'
                      : 'i-carbon-renew'
                  "
                ></div>
                {{ $t('rss.refresh') }}
              </AbButton>
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
        @update:checked-row-keys="(e) => (selectedRSS = (e as number[]))"
      ></NDataTable>

      <div v-if="selectedRSS.length > 0">
        <div class="divider"></div>
        <div class="rss-actions">
          <AbButton variant="primary" @click="enableSelected">{{
            $t('rss.enable')
          }}</AbButton>
          <AbButton variant="secondary" @click="disableSelected">{{
            $t('rss.disable')
          }}</AbButton>
          <AbButton variant="danger" @click="onDeleteSelected">{{
            $t('rss.delete')
          }}</AbButton>
        </div>
      </div>
    </ab-container>
  </div>
</template>

<style lang="scss" scoped>
.page-rss {
  overflow: auto;
  flex-grow: 1;
}

:deep(.rss-name-cell) {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;

  .rss-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.divider {
  width: 100%;
  height: 1px;
  background: var(--color-border);
  margin: 12px 0;
}

.rss-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;

  @include forTablet {
    gap: 10px;
  }
}

// Mobile RSS card styles
.rss-card-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rss-card-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rss-card-url {
  font-size: 12px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rss-card-error {
  font-size: 12px;
  color: var(--color-warning-text-secondary);
  word-break: break-word;
}

.rss-card-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.rss-card-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 4px;
}
</style>
