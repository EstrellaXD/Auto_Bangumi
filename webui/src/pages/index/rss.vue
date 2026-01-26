<script lang="tsx" setup>
import { type DataTableColumns, NDataTable, NTooltip } from 'naive-ui';
import type { RSS } from '#/rss';

definePage({
  name: 'RSS',
});

const { t } = useMyI18n();
const { isMobile } = useBreakpointQuery();
const { rss, selectedRSS } = storeToRefs(useRSSStore());
const { getAll, deleteSelected, disableSelected, enableSelected } =
  useRSSStore();

onActivated(() => {
  getAll();
});

const rssColumns = computed<DataTableColumns<RSS>>(() => [
  {
    type: 'selection',
  },
  {
    title: t('rss.name'),
    key: 'name',
    className: 'text-h3',
    ellipsis: {
      tooltip: true,
    },
  },
  {
    title: t('rss.url'),
    key: 'url',
    className: 'text-h3',
    minWidth: 400,
    align: 'center',
    ellipsis: {
      tooltip: true,
    },
  },
  {
    title: t('rss.status'),
    key: 'status',
    className: 'text-h3',
    align: 'right',
    minWidth: 200,
    render(rss: RSS) {
      return (
        <div flex="~ justify-end gap-x-8">
          {rss.parser && <ab-tag type="primary" title={rss.parser} />}
          {rss.aggregate && <ab-tag type="primary" title="aggregate" />}
          {rss.connection_status === 'healthy' && (
            <ab-tag type="active" title={t('rss.connected')} />
          )}
          {rss.connection_status === 'error' && (
            <NTooltip>
              {{
                trigger: () => <ab-tag type="warn" title={t('rss.error')} />,
                default: () => rss.last_error || 'Unknown error',
              }}
            </NTooltip>
          )}
          {rss.enabled ? (
            <ab-tag type="active" title="active" />
          ) : (
            <ab-tag type="inactive" title="inactive" />
          )}
        </div>
      );
    },
  },
]);

const rssRowKey = (row: RSS) => row.id;
</script>

<template>
  <div class="page-rss">
    <ab-container :title="$t('rss.title')">
      <!-- Mobile: Card-based list -->
      <ab-data-list
        v-if="isMobile"
        :items="rss || []"
        :columns="[
          { key: 'name', title: t('rss.name') },
          { key: 'url', title: t('rss.url') },
        ]"
        :selectable="true"
        key-field="id"
        @select="(keys) => (selectedRSS = keys as number[])"
      >
        <template #item="{ item }">
          <div class="rss-card-content">
            <div class="rss-card-name">{{ item.name }}</div>
            <div class="rss-card-url">{{ item.url }}</div>
            <div class="rss-card-tags">
              <ab-tag v-if="item.parser" type="primary" :title="item.parser" />
              <ab-tag v-if="item.aggregate" type="primary" title="aggregate" />
              <ab-tag
                v-if="item.connection_status === 'healthy'"
                type="active"
                :title="$t('rss.connected')"
              />
              <NTooltip v-if="item.connection_status === 'error'">
                <template #trigger>
                  <ab-tag type="warn" :title="$t('rss.error')" />
                </template>
                {{ item.last_error || 'Unknown error' }}
              </NTooltip>
              <ab-tag
                :type="item.enabled ? 'active' : 'inactive'"
                :title="item.enabled ? 'active' : 'inactive'"
              />
            </div>
          </div>
        </template>
      </ab-data-list>

      <!-- Desktop: Data table -->
      <NDataTable
        v-else
        :columns="rssColumns"
        :data="rss"
        :row-key="rssRowKey"
        :pagination="false"
        :bordered="false"
        :max-height="500"
        @update:checked-row-keys="(e) => (selectedRSS = (e as number[]))"
      ></NDataTable>

      <div v-if="selectedRSS.length > 0">
        <div class="divider"></div>
        <div class="rss-actions">
          <ab-button @click="enableSelected">{{ $t('rss.enable') }}</ab-button>
          <ab-button @click="disableSelected">{{
            $t('rss.disable')
          }}</ab-button>
          <ab-button type="warn" @click="deleteSelected">{{
            $t('rss.delete')
          }}</ab-button>
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

.rss-card-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-top: 4px;
}
</style>
