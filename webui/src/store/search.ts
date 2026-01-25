import type { BangumiRule, SearchResult } from '#/bangumi';

// Filter types
export interface SearchFilters {
  group: string[];
  resolution: string[];
  subtitleType: string[];
  season: string[];
}

export interface FilterOptions {
  group: string[];
  resolution: string[];
  subtitleType: string[];
  season: string[];
}

// Grouped bangumi result
export interface GroupedBangumi {
  key: string;
  official_title: string;
  poster_link: string;
  year?: string | null;
  variants: BangumiRule[];
}

// Helper to parse metadata from title/bangumi
function parseResolution(bangumi: BangumiRule): string {
  // Check dpi field first
  if (bangumi.dpi) {
    return bangumi.dpi;
  }
  // Parse from title_raw
  const title = bangumi.title_raw || '';
  const resMatch = title.match(/\b(4K|2160p|1080p|720p|480p)\b/i);
  return resMatch ? resMatch[1].toLowerCase() : '';
}

function parseSubtitleType(bangumi: BangumiRule): string {
  // Check subtitle field first
  if (bangumi.subtitle) {
    const sub = bangumi.subtitle.toLowerCase();
    if (sub.includes('简') || sub.includes('chs') || sub.includes('sc')) return '简中';
    if (sub.includes('繁') || sub.includes('cht') || sub.includes('tc')) return '繁中';
    if (sub.includes('双语') || sub.includes('dual')) return '双语';
  }
  // Parse from title_raw
  const title = bangumi.title_raw || '';
  if (/简体|简中|CHS|SC/i.test(title)) return '简中';
  if (/繁體|繁中|CHT|TC/i.test(title)) return '繁中';
  if (/双语|Dual/i.test(title)) return '双语';
  if (/内嵌|内封/i.test(title)) return '内嵌';
  if (/外挂|ASS|SRT/i.test(title)) return '外挂';
  return '';
}

function parseSeason(bangumi: BangumiRule): string {
  if (bangumi.season_raw) {
    return bangumi.season_raw;
  }
  if (bangumi.season) {
    return `S${bangumi.season}`;
  }
  // Parse from title
  const title = bangumi.title_raw || '';
  if (/剧场版|Movie|劇場版/i.test(title)) return '剧场版';
  if (/OVA/i.test(title)) return 'OVA';
  const seasonMatch = title.match(/S(\d+)|Season\s*(\d+)|第(\d+)季/i);
  if (seasonMatch) {
    const num = seasonMatch[1] || seasonMatch[2] || seasonMatch[3];
    return `S${num}`;
  }
  return '';
}

export const useSearchStore = defineStore('search', () => {
  const providers = ref<string[]>(['mikan', 'dmhy', 'nyaa']);

  const {
    keyword,
    provider,
    open: openSearch,
    close: closeSearch,
    data: searchData,
    status,
  } = apiSearch.get();

  provider.value = providers.value[0];

  // Modal state
  const showModal = ref(false);
  const selectedResult = ref<BangumiRule | null>(null);
  const selectedGroup = ref<GroupedBangumi | null>(null);

  // Filter state for selected group variants
  const variantFilters = ref<SearchFilters>({
    group: [],
    resolution: [],
    subtitleType: [],
    season: [],
  });

  const loading = computed(() => status.value !== 'CLOSED');

  // Raw bangumi list with order
  const bangumiList = computed<SearchResult[]>(() =>
    searchData.value.map((item, index) => ({ order: index, value: item }))
  );

  // Group results by official_title
  const groupedResults = computed<GroupedBangumi[]>(() => {
    const map = new Map<string, BangumiRule[]>();

    for (const item of searchData.value) {
      const key = item.official_title || item.title_raw || '';
      if (!map.has(key)) {
        map.set(key, []);
      }
      map.get(key)!.push(item);
    }

    const groups: GroupedBangumi[] = [];
    for (const [key, variants] of map) {
      // Use the first variant's poster and info
      const first = variants[0];
      groups.push({
        key,
        official_title: first.official_title || first.title_raw || '',
        poster_link: first.poster_link || '',
        year: first.year,
        variants,
      });
    }

    return groups;
  });

  // Extract filter options from selected group's variants
  const variantFilterOptions = computed<FilterOptions>(() => {
    if (!selectedGroup.value) {
      return { group: [], resolution: [], subtitleType: [], season: [] };
    }

    const groups = new Set<string>();
    const resolutions = new Set<string>();
    const subtitleTypes = new Set<string>();
    const seasons = new Set<string>();

    for (const item of selectedGroup.value.variants) {
      if (item.group_name) groups.add(item.group_name);

      const res = parseResolution(item);
      if (res) resolutions.add(res);

      const subType = parseSubtitleType(item);
      if (subType) subtitleTypes.add(subType);

      const season = parseSeason(item);
      if (season) seasons.add(season);
    }

    return {
      group: Array.from(groups).sort(),
      resolution: Array.from(resolutions).sort((a, b) => {
        const order = ['4k', '2160p', '1080p', '720p', '480p'];
        return order.indexOf(a.toLowerCase()) - order.indexOf(b.toLowerCase());
      }),
      subtitleType: Array.from(subtitleTypes),
      season: Array.from(seasons).sort(),
    };
  });

  // Filtered variants based on selected filters
  const filteredVariants = computed<BangumiRule[]>(() => {
    if (!selectedGroup.value) return [];

    const hasFilters = Object.values(variantFilters.value).some((arr) => arr.length > 0);
    if (!hasFilters) {
      return selectedGroup.value.variants;
    }

    return selectedGroup.value.variants.filter((bangumi) => {
      // Group filter
      if (variantFilters.value.group.length > 0) {
        if (!bangumi.group_name || !variantFilters.value.group.includes(bangumi.group_name)) {
          return false;
        }
      }

      // Resolution filter
      if (variantFilters.value.resolution.length > 0) {
        const res = parseResolution(bangumi);
        if (!res || !variantFilters.value.resolution.includes(res)) {
          return false;
        }
      }

      // Subtitle type filter
      if (variantFilters.value.subtitleType.length > 0) {
        const subType = parseSubtitleType(bangumi);
        if (!subType || !variantFilters.value.subtitleType.includes(subType)) {
          return false;
        }
      }

      // Season filter
      if (variantFilters.value.season.length > 0) {
        const season = parseSeason(bangumi);
        if (!season || !variantFilters.value.season.includes(season)) {
          return false;
        }
      }

      return true;
    });
  });

  async function getProviders() {
    providers.value = await apiSearch.getProvider();
    provider.value = providers.value[0];
  }

  function openModal() {
    showModal.value = true;
  }

  function closeModal() {
    showModal.value = false;
    selectedResult.value = null;
  }

  function toggleModal() {
    if (showModal.value) {
      closeModal();
    } else {
      openModal();
    }
  }

  function clearSearch() {
    keyword.value = '';
    searchData.value = [];
    variantFilters.value = { group: [], resolution: [], subtitleType: [], season: [] };
    selectedGroup.value = null;
    closeSearch();
  }

  function toggleVariantFilter(category: keyof SearchFilters, value: string) {
    const arr = variantFilters.value[category];
    const index = arr.indexOf(value);
    if (index === -1) {
      arr.push(value);
    } else {
      arr.splice(index, 1);
    }
  }

  function clearVariantFilters() {
    variantFilters.value = { group: [], resolution: [], subtitleType: [], season: [] };
  }

  function selectGroup(group: GroupedBangumi) {
    selectedGroup.value = group;
    variantFilters.value = { group: [], resolution: [], subtitleType: [], season: [] };
  }

  function clearSelectedGroup() {
    selectedGroup.value = null;
    variantFilters.value = { group: [], resolution: [], subtitleType: [], season: [] };
  }

  function selectResult(bangumi: BangumiRule) {
    selectedResult.value = bangumi;
  }

  function clearSelectedResult() {
    selectedResult.value = null;
  }

  return {
    // State
    inputValue: keyword,
    loading,
    provider,
    providers,
    bangumiList,
    groupedResults,
    selectedGroup,
    variantFilters,
    variantFilterOptions,
    filteredVariants,
    showModal,
    selectedResult,

    // Actions
    clearSearch,
    getProviders,
    onSearch: openSearch,
    closeSearch,
    openModal,
    closeModal,
    toggleModal,
    toggleVariantFilter,
    clearVariantFilters,
    selectGroup,
    clearSelectedGroup,
    selectResult,
    clearSelectedResult,
  };
});
