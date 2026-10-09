<script lang="ts" setup>
import { Left } from '@icon-park/vue-next';
import MarketConfirm from '@/components/market/market-confirm.vue';
import type { ApiError } from '#/api';
import type { CatalogEntry, PluginInfo } from '#/plugins';
import { apiPlugins } from '@/api/plugins';
import { refreshPluginProviders } from '@/hooks/usePluginProviders';
import { refreshPluginUi } from '@/hooks/usePluginUi';
import { idLabel } from '@/utils/id-label';
import { renderMarkdown } from '@/utils/markdown';
import {
  MARKET_CATEGORIES,
  MARKET_STATES,
  type MarketCategory,
  type MarketState,
  categoryCounts,
  entryState,
  filterEntries,
  readCachedCatalog,
  sourceUrl,
  writeCachedCatalog,
} from '@/utils/plugin-market';
import { relativeTime } from '@/utils/relative-time';

definePage({
  name: 'Market',
});

const { t, lang } = useMyI18n();
const message = useMessage();
const route = useRoute();
const router = useRouter();
const { isMobile } = useBreakpointQuery();
const { refreshGroup } = useConfigStore();

// 目录：成功获取后写入 localStorage；目录不可达时显示上一次的目录（stale），
// 此时安装与更新不可用。error 为 null 表示最近一次获取成功，'' 表示失败但后端没给原因。
const catalog = ref<CatalogEntry[] | null>(null);
const fetchedAt = ref(0);
const loading = ref(false);
const error = ref<string | null>(null);
const stale = computed(() => error.value !== null && catalog.value !== null);

const installed = ref<PluginInfo[]>([]);

async function loadCatalog() {
  loading.value = true;
  try {
    const entries = await apiPlugins.catalog();
    catalog.value = entries;
    fetchedAt.value = Date.now();
    error.value = null;
    writeCachedCatalog({ entries, fetchedAt: fetchedAt.value });
  } catch (e) {
    // axios 拦截器把失败归一成 ApiError，后端原因在 detail
    error.value = (e as ApiError).detail ?? '';
    const cached = catalog.value ? null : readCachedCatalog();
    if (cached) {
      catalog.value = cached.entries;
      fetchedAt.value = cached.fetchedAt;
    }
  } finally {
    loading.value = false;
  }
}

async function loadInstalled() {
  try {
    installed.value = (await apiPlugins.list()).plugins;
  } catch {
    // 只用于更新确认中的权限对比；失败时按“没有旧权限”处理，新增权限都需确认
  }
}

onMounted(() => Promise.all([loadCatalog(), loadInstalled()]));

// 页面被 KeepAlive 缓存；再次进入时按本机插件同步安装状态（设置页可能卸载过），不重新下载目录
let activated = false;
onActivated(async () => {
  if (!activated) {
    activated = true;
    return;
  }
  await loadInstalled();
  if (!catalog.value) return;
  catalog.value = catalog.value.map((entry) => ({
    ...entry,
    installed_version:
      installed.value.find((p) => p.id === entry.id && p.source === 'catalog')
        ?.version ?? null,
  }));
});

// 相对时间每分钟刷新一次
const now = ref(Date.now());
useIntervalFn(() => (now.value = Date.now()), 60_000);
const updatedText = computed(() =>
  relativeTime(t, fetchedAt.value, Math.max(now.value, fetchedAt.value))
);
const cachedAt = computed(() =>
  new Date(fetchedAt.value).toLocaleString(lang.value, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
);

// 筛选（分类与状态的取值来自下面的选项，模型类型是 string）
const query = ref('');
const category = ref<string>('all');
const state = ref<string>('all');
const filter = computed(() => ({
  query: query.value,
  category: category.value as MarketCategory | 'all',
  state: state.value as MarketState | 'all',
}));

const counts = computed(() =>
  categoryCounts(catalog.value ?? [], filter.value)
);
const categoryOptions = computed(() => [
  {
    value: 'all',
    label: `${t('market.category_all')} ${counts.value.all}`,
  },
  ...MARKET_CATEGORIES.filter(
    (c) => counts.value[c] > 0 || c === category.value
  ).map((c) => ({
    value: c,
    label: `${t(`market.category.${c}`)} ${counts.value[c]}`,
  })),
]);
const stateOptions = computed(() => [
  { value: 'all', label: t('market.state_all') },
  ...MARKET_STATES.map((s) => ({ value: s, label: t(`market.state.${s}`) })),
]);

const visible = computed(() =>
  filterEntries(catalog.value ?? [], filter.value)
);

function resetFilters() {
  query.value = '';
  category.value = 'all';
  state.value = 'all';
}

// 选中项：/market/:id；桌面上没有 id 时默认显示列表第一项
const routeId = computed(
  () => (route.params as Record<string, string | undefined>).id
);
const selected = computed(() => {
  const list = catalog.value ?? [];
  if (routeId.value) return list.find((e) => e.id === routeId.value) ?? null;
  return isMobile.value ? null : visible.value[0] ?? null;
});
const showDetail = computed(() => isMobile.value && Boolean(routeId.value));

const confirming = ref(false);
watch(routeId, () => (confirming.value = false));

function back() {
  if ((window.history.state as { back?: unknown } | null)?.back) router.back();
  else router.replace('/market');
}

function stateLabel(entry: CatalogEntry) {
  const s = entryState(entry);
  return s === 'update'
    ? t('market.update_from', { version: entry.installed_version })
    : t(`market.state.${s}`);
}

const installedPermissions = computed(
  () =>
    installed.value.find((p) => p.id === selected.value?.id)?.permissions ?? []
);

const primaryLabel = computed(() =>
  selected.value
    ? t(
        {
          available: 'market.install',
          update: 'market.update',
          installed: 'market.state.installed',
        }[entryState(selected.value)]
      )
    : ''
);
// 已是最新，或目录不可达（安装需要联网）
const primaryDisabled = computed(
  () =>
    !selected.value || entryState(selected.value) === 'installed' || stale.value
);

const readme = computed(() =>
  selected.value?.readme ? renderMarkdown(selected.value.readme) : ''
);

// 安装/更新
const busy = ref(false);

async function install(entry: CatalogEntry) {
  const name = entry.name || entry.id;
  const updating = entry.installed_version !== null;
  busy.value = true;
  try {
    installed.value = (await apiPlugins.install(entry.id)).plugins;
  } catch {
    // 后端的具体原因（如验签失败）由 axios 拦截器另行提示
    message.error(
      t(updating ? 'market.update_failed' : 'market.install_failed', { name })
    );
    busy.value = false;
    return;
  }
  message.success(
    updating
      ? t('market.update_success', { name, version: entry.version })
      : t('market.install_success', { name })
  );
  confirming.value = false;
  busy.value = false;
  // 与设置页插件卡片相同：同步 config store 的 plugins 段、Provider 候选与前端挂载点
  await Promise.all([
    loadCatalog(),
    refreshGroup('plugins', ['allow_unsigned', 'enabled', 'options']),
    refreshPluginProviders(),
    refreshPluginUi(),
  ]);
}

function pointLabel(id: string) {
  return idLabel(t, 'config.plugins_set.point_labels', id);
}

function permissionLabel(id: string) {
  return idLabel(t, 'config.plugins_set.permission_labels', id);
}
</script>

<template>
  <div class="market" :class="{ 'market--detail': showDetail }">
    <!-- 手机：详情是单独一屏，顶部返回 -->
    <header v-if="showDetail" class="market__bar">
      <ab-icon-button :label="$t('market.back')" @click="back">
        <Left :size="20" />
      </ab-icon-button>
      <h1 class="market__bar-title">
        {{ selected ? selected.name || selected.id : $t('market.title') }}
      </h1>
    </header>

    <template v-else>
      <!-- 桌面：搜索 | 状态 | 目录状态；手机：标题 | 目录状态，下一行搜索 | 状态 -->
      <header class="market__top">
        <h1 v-if="isMobile" class="market__title">{{ $t('market.title') }}</h1>
        <div class="market__meta">
          <span
            v-if="catalog && !stale"
            class="market__verified"
            :title="$t('market.catalog_verified')"
          >
            <span class="mark mark--installed" aria-hidden="true"></span>
            <span class="market__verified-text"
              >{{ $t('market.catalog_verified') }} ·</span
            >
            <span class="market__time">{{
              $t('market.updated', { time: updatedText })
            }}</span>
          </span>
          <ab-button
            size="sm"
            variant="ghost"
            :loading="loading"
            @click="loadCatalog"
          >
            {{ $t('market.refresh') }}
          </ab-button>
        </div>
        <ab-input
          v-model="query"
          clearable
          class="market__search"
          :placeholder="$t('market.search')"
          :aria-label="$t('market.search')"
        />
        <ab-select
          v-model="state"
          class="market__state"
          :options="stateOptions"
          :aria-label="$t('market.state_filter')"
        />
      </header>

      <ab-segmented
        v-if="catalog?.length"
        v-model:value="category"
        size="sm"
        class="market__tabs"
        :options="categoryOptions"
        :aria-label="$t('market.categories')"
      />
    </template>

    <ab-alert v-if="stale" type="warning" :title="$t('market.stale_lead')">
      {{ $t('market.stale', { time: cachedAt }) }}
      <span v-if="error" class="market__error">{{ error }}</span>
      <template #action>
        <ab-button size="sm" :loading="loading" @click="loadCatalog">
          {{ $t('market.retry') }}
        </ab-button>
      </template>
    </ab-alert>

    <ab-skeleton v-if="!catalog && loading" preset="row" :count="5" />

    <ab-empty
      v-else-if="!catalog && error !== null"
      :title="$t('market.load_failed')"
      :description="$t('market.load_failed_hint')"
    >
      <template #action>
        <p v-if="error" class="market__error">{{ error }}</p>
        <ab-button size="sm" :loading="loading" @click="loadCatalog">
          {{ $t('market.retry') }}
        </ab-button>
      </template>
    </ab-empty>

    <div v-else-if="catalog" class="market__panes">
      <nav
        v-if="!showDetail"
        class="market__list"
        :aria-label="$t('market.list_label')"
      >
        <RouterLink
          v-for="entry in visible"
          :key="entry.id"
          :to="`/market/${encodeURIComponent(entry.id)}`"
          :replace="!isMobile"
          class="row"
          :class="{ 'row--on': !isMobile && selected?.id === entry.id }"
          :aria-current="
            !isMobile && selected?.id === entry.id ? 'true' : undefined
          "
        >
          <span class="row__name">{{ entry.name || entry.id }}</span>
          <span class="row__version">{{ entry.version }}</span>
          <span class="row__state">
            <span
              class="mark"
              :class="`mark--${entryState(entry)}`"
              aria-hidden="true"
            ></span>
            {{ stateLabel(entry) }}
          </span>
          <span class="row__author">{{ entry.authors.join(', ') }}</span>
        </RouterLink>

        <ab-empty
          v-if="!visible.length && query.trim()"
          :title="$t('market.no_match', { query: query.trim() })"
        >
          <template #action>
            <ab-button size="sm" variant="ghost" @click="query = ''">
              {{ $t('market.clear_search') }}
            </ab-button>
          </template>
        </ab-empty>
        <ab-empty
          v-else-if="!visible.length && catalog.length"
          :title="$t('market.no_filter_match')"
        >
          <template #action>
            <ab-button size="sm" variant="ghost" @click="resetFilters">
              {{ $t('market.show_all') }}
            </ab-button>
          </template>
        </ab-empty>
        <ab-empty v-else-if="!catalog.length" :title="$t('market.empty')" />
      </nav>

      <section
        v-if="selected && (!isMobile || showDetail)"
        class="market__detail"
      >
        <MarketConfirm
          v-if="confirming"
          :key="selected.id"
          :entry="selected"
          :installed-permissions="installedPermissions"
          :busy="busy"
          @back="confirming = false"
          @confirm="install(selected)"
        />

        <template v-else>
          <header class="detail__head">
            <div class="detail__heading">
              <h2 v-if="!isMobile" class="detail__title">
                {{ selected.name || selected.id }}
              </h2>
              <p v-if="selected.description" class="detail__desc">
                {{ selected.description }}
              </p>
            </div>
            <ab-button
              v-if="!isMobile"
              variant="primary"
              :disabled="primaryDisabled"
              @click="confirming = true"
            >
              {{ primaryLabel }}
            </ab-button>
          </header>

          <dl class="detail__kv">
            <dt>{{ $t('market.version') }}</dt>
            <dd class="detail__mono">
              {{
                selected.sdk
                  ? $t('market.version_sdk', {
                      version: selected.version,
                      sdk: selected.sdk,
                    })
                  : selected.version
              }}
            </dd>

            <template v-if="selected.authors.length">
              <dt>{{ $t('market.authors') }}</dt>
              <dd>{{ selected.authors.join(', ') }}</dd>
            </template>

            <template v-if="selected.repo && selected.commit">
              <dt>{{ $t('market.source') }}</dt>
              <dd>
                <a
                  class="detail__link"
                  :href="sourceUrl(selected)"
                  target="_blank"
                  rel="noopener noreferrer"
                  >{{ selected.repo }}@{{ selected.commit.slice(0, 7) }}
                  <span aria-hidden="true">↗</span></a
                >
              </dd>
            </template>

            <dt>{{ $t('market.extension_points') }}</dt>
            <dd class="detail__tags">
              <!-- ab-tag 的 title 是文字内容，原始 id 的提示放在外层 -->
              <span
                v-for="id in selected.extension_points"
                :key="id"
                :title="id"
              >
                <ab-tag>{{ pointLabel(id) }}</ab-tag>
              </span>
              <span
                v-if="!selected.extension_points.length"
                class="detail__muted"
              >
                {{ $t('market.none') }}
              </span>
            </dd>

            <dt>{{ $t('market.permissions') }}</dt>
            <dd class="detail__tags">
              <span v-for="id in selected.permissions" :key="id" :title="id">
                <ab-tag>{{ permissionLabel(id) }}</ab-tag>
              </span>
              <span v-if="!selected.permissions.length" class="detail__muted">
                {{ $t('market.none') }}
              </span>
            </dd>

            <dt>{{ $t('market.frontend') }}</dt>
            <dd>{{ selected.has_web ? $t('market.yes') : $t('market.no') }}</dd>
          </dl>

          <!-- renderMarkdown 先转义全部 HTML，只输出白名单标签与 http(s) 链接 -->
          <!-- eslint-disable-next-line vue/no-v-html -->
          <article v-if="readme" class="readme" v-html="readme"></article>

          <div v-if="isMobile" class="detail__sticky">
            <ab-button
              variant="primary"
              block
              :disabled="primaryDisabled"
              @click="confirming = true"
            >
              {{ primaryLabel }}
            </ab-button>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.market {
  display: flex;
  flex-direction: column;
  flex-grow: 1;
  gap: 12px;
  min-height: 0;
  overflow: auto;
}

.market__top {
  display: grid;
  grid-template-areas:
    'title meta'
    'search state';
  grid-template-columns: minmax(0, 1fr) 128px;
  align-items: center;
  gap: 8px;

  @include forTablet {
    grid-template-areas: 'search state meta';
    grid-template-columns: minmax(0, 1fr) 140px auto;
    gap: 8px 12px;
  }
}

.market__title,
.market__bar-title {
  margin: 0;
  font-size: 18px;
  font-weight: 650;
}

.market__title {
  grid-area: title;
}

.market__meta {
  display: flex;
  grid-area: meta;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  color: var(--color-text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.market__verified {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

// 手机上标题旁放不下：只留色块与时间，文字留给读屏（与 title 提示）
.market__verified-text {
  @include forMobile {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
}

.market__time {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.market__search {
  grid-area: search;
  width: 100%;
  min-width: 0;
}

.market__state {
  grid-area: state;
}

// 后端给出的原因（英文原文），单独一行
.market__error {
  display: block;
  margin: 4px 0 8px;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.market__bar {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.market__bar-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

// 桌面：列表 + 详情双栏，各自滚动；手机：只显示其中一栏
.market__panes {
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: minmax(0, 1fr);
  flex: 1;
  min-height: 0;

  @include forTablet {
    grid-template-columns: minmax(260px, 320px) 1fr;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    overflow: hidden;
  }
}

.market__list {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: auto;

  @include forTablet {
    border-right: 1px solid var(--color-border);
  }
}

.row {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: baseline;
  gap: 2px 10px;
  min-height: var(--touch-target);
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text);
  text-decoration: none;
  transition: background-color var(--transition-fast);

  &:hover {
    background: var(--color-surface-2);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: -2px;
  }

  @include forMobile {
    padding: 10px 4px;
  }
}

.row--on {
  background: var(--color-surface-2);
  box-shadow: inset 2px 0 0 var(--color-primary);
}

.row__name {
  min-width: 0;
  overflow: hidden;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row__version,
.detail__mono {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.row__version {
  color: var(--color-text-secondary);
  font-size: 12px;
  text-align: right;
}

.row__state {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  white-space: nowrap;
}

.row__author {
  min-width: 0;
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: 12px;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

// Soft Ink 状态标记：方形色块 + 墨色文字
.mark {
  display: inline-block;
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 2px;
}

.mark--installed {
  background: var(--color-success);
}

.mark--update {
  background: var(--color-warning);
}

.mark--available {
  background: var(--color-text-muted);
}

.market__detail {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
  min-height: 0;
  overflow: auto;

  @include forTablet {
    padding: 16px 20px 0;
  }
}

.detail__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.detail__heading {
  min-width: 0;
}

.detail__title {
  margin: 0;
  font-size: 17px;
  font-weight: 650;
}

.detail__desc {
  margin: 2px 0 0;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.detail__kv {
  display: grid;
  grid-template-columns: minmax(64px, max-content) 1fr;
  gap: 8px 14px;
  margin: 0;
  font-size: 13px;

  dt {
    color: var(--color-text-secondary);
  }

  dd {
    min-width: 0;
    margin: 0;
  }
}

.detail__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.detail__muted {
  color: var(--color-text-secondary);
}

.detail__link {
  color: var(--color-text);
  font-family: var(--font-mono);
  font-size: 12px;
  text-decoration: underline;
  text-decoration-color: var(--color-text-muted);
  text-underline-offset: 3px;
  overflow-wrap: anywhere;

  &:hover {
    text-decoration-color: currentColor;
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }
}

// 手机：主操作固定在详情滚动区的底部（底部导航之上）
.detail__sticky {
  position: sticky;
  bottom: 0;
  z-index: var(--z-sticky);
  margin-top: auto;
  padding: 10px 0;
  border-top: 1px solid var(--color-border);
  background: var(--color-bg);
}

.readme {
  padding: 12px 0 16px;
  border-top: 1px solid var(--color-border);
  font-size: 13px;
  line-height: 1.6;
  overflow-wrap: anywhere;

  :deep(h3),
  :deep(h4),
  :deep(h5),
  :deep(h6) {
    margin: 12px 0 4px;
    font-size: 14px;
    font-weight: 650;
  }

  :deep(h3:first-child) {
    margin-top: 0;
  }

  :deep(p),
  :deep(ul),
  :deep(ol) {
    margin: 0 0 8px;
  }

  :deep(ul),
  :deep(ol) {
    padding-left: 20px;
  }

  :deep(ul) {
    list-style: disc;
  }

  :deep(ol) {
    list-style: decimal;
  }

  :deep(code) {
    font-family: var(--font-mono);
    font-size: 12px;
  }

  :deep(pre) {
    margin: 0 0 8px;
    padding: 8px 10px;
    border-radius: var(--radius-sm);
    background: var(--color-surface-2);
    overflow-x: auto;
  }

  :deep(a) {
    color: var(--color-primary);
  }
}
</style>
