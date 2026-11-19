import type { CatalogEntry } from '#/plugins';

/** 插件市场的分类：按扩展点归成几个用户能理解的大类 */
export type MarketCategory =
  | 'source'
  | 'notify'
  | 'organize'
  | 'interface'
  | 'other';
export type MarketState = 'installed' | 'update' | 'available';

export const MARKET_CATEGORIES: MarketCategory[] = [
  'source',
  'notify',
  'organize',
  'interface',
  'other',
];
export const MARKET_STATES: MarketState[] = [
  'installed',
  'update',
  'available',
];

// 扩展点 id（ab_sdk.points）→ 分类；未列出的扩展点归入 other
const POINT_CATEGORY: Record<string, MarketCategory> = {
  search_site: 'source',
  metadata_provider: 'source',
  'http.request': 'source',
  notifier: 'notify',
  message_template: 'notify',
  rename_strategy: 'organize',
  media_files: 'organize',
  conflict_policy: 'organize',
  api_router: 'interface',
  mcp_tool: 'interface',
  mcp_resource: 'interface',
};

/** 插件所属的分类；有多个扩展点的插件可属于多个分类 */
export function categoriesOf(entry: CatalogEntry): MarketCategory[] {
  const found = new Set(
    entry.extension_points.map((p) => POINT_CATEGORY[p] ?? 'other')
  );
  if (entry.has_web) found.add('interface');
  if (!found.size) found.add('other');
  return MARKET_CATEGORIES.filter((c) => found.has(c));
}

export function entryState(entry: CatalogEntry): MarketState {
  if (!entry.installed_version) return 'available';
  // 本机版本比目录新（目录回退过）时不提示更新，避免“更新”成旧版本
  return entry.installed_version !== entry.version && entry.update_available
    ? 'update'
    : 'installed';
}

export interface MarketFilter {
  query: string;
  category: MarketCategory | 'all';
  state: MarketState | 'all';
}

function matchesQuery(entry: CatalogEntry, query: string) {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return [entry.name, entry.id, entry.description, ...entry.authors].some(
    (text) => text.toLowerCase().includes(q)
  );
}

/** 搜索与状态筛选后，各分类（及“全部”）的插件数；“全部”中每个插件只算一次 */
export function categoryCounts(
  entries: CatalogEntry[],
  filter: Omit<MarketFilter, 'category'>
): Record<MarketCategory | 'all', number> {
  const counts = {
    all: 0,
    source: 0,
    notify: 0,
    organize: 0,
    interface: 0,
    other: 0,
  };
  for (const entry of filterEntries(entries, { ...filter, category: 'all' })) {
    counts.all += 1;
    for (const c of categoriesOf(entry)) counts[c] += 1;
  }
  return counts;
}

export function filterEntries(
  entries: CatalogEntry[],
  { query, category, state }: MarketFilter
): CatalogEntry[] {
  return entries.filter(
    (entry) =>
      (category === 'all' || categoriesOf(entry).includes(category)) &&
      (state === 'all' || entryState(entry) === state) &&
      matchesQuery(entry, query)
  );
}

/** 更新前后声明的权限差异 */
export function permissionDiff(before: string[], after: string[]) {
  return {
    kept: after.filter((p) => before.includes(p)),
    added: after.filter((p) => !before.includes(p)),
    removed: before.filter((p) => !after.includes(p)),
  };
}

/** GitHub 上插件源码的位置：仓库、固定的 commit 与子目录 */
export function sourceUrl(entry: CatalogEntry): string {
  const path = entry.path && entry.path !== '.' ? `/${entry.path}` : '';
  return `https://github.com/${entry.repo}/tree/${entry.commit}${path}`;
}

// 上一次成功获取的目录：目录不可达时仍可浏览（安装需要联网，届时禁用）
const CACHE_KEY = 'plugin_market_catalog';

export interface CachedCatalog {
  entries: CatalogEntry[];
  fetchedAt: number;
}

export function readCachedCatalog(): CachedCatalog | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? (JSON.parse(raw) as CachedCatalog) : null;
  } catch {
    return null;
  }
}

export function writeCachedCatalog(cache: CachedCatalog) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
  } catch {
    // 隐私模式或存储已满：只是少了离线缓存
  }
}
