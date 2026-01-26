<script lang="ts" setup>
import {
  Format,
  Me,
  Pause,
  PlayOne,
  Power,
  Refresh,
  Search,
} from '@icon-park/vue-next';
import { ruleTemplate } from '#/bangumi';

const { t, changeLocale } = useMyI18n();
const { running, onUpdate, offUpdate } = useAppInfo();
const { showAddRss: showAddRSS, closeAddRss } = useAddRss();
const { toggleModal: openSearch } = useSearchStore();
const { isMobile } = useBreakpointQuery();

const showAccount = ref(false);
const rssRule = ref(ruleTemplate);

const { start, pause, shutdown, restart, resetRule } = useProgramStore();
const { refreshPoster } = useBangumiStore();

const items = [
  {
    id: 1,
    label: () => t('topbar.start'),
    icon: PlayOne,
    handle: start,
  },
  {
    id: 2,
    label: () => t('topbar.pause'),
    icon: Pause,
    handle: pause,
  },
  {
    id: 3,
    label: () => t('topbar.restart'),
    icon: Refresh,
    handle: restart,
  },
  {
    id: 4,
    label: () => t('topbar.shutdown'),
    icon: Power,
    handle: shutdown,
  },
  {
    id: 5,
    label: () => t('topbar.refresh_poster'),
    icon: Refresh,
    handle: refreshPoster,
  },
  {
    id: 6,
    label: () => t('topbar.reset_rule'),
    icon: Format,
    handle: resetRule,
  },
  {
    id: 7,
    label: () => t('topbar.profile.title'),
    icon: Me,
    handle: () => {
      showAccount.value = true;
    },
  },
];

const { isDark } = useDarkMode();
const onSearchFocus = ref(false);

watch(showAddRSS, (val) => {
  if (!val) {
    rssRule.value = ruleTemplate;
    closeAddRss();
  }
});

onBeforeMount(() => {
  onUpdate();
});

onUnmounted(() => {
  offUpdate();
});
</script>

<template>
  <div class="topbar">
    <!-- Logo -->
    <div class="topbar-brand">
      <img
        :src="isDark ? '/images/logo-light.svg' : '/images/logo.svg'"
        alt="favicon"
        class="topbar-logo"
      />
      <img
        v-if="!isMobile"
        v-show="onSearchFocus === false"
        :src="isDark ? '/images/AutoBangumi.svg' : '/images/AutoBangumi-dark.svg'"
        alt="AutoBangumi"
        class="topbar-wordmark"
      />
    </div>

    <!-- Desktop search bar -->
    <div class="topbar-search">
      <ab-search-bar />
    </div>

    <!-- Mobile search button (fills space) -->
    <button
      v-if="isMobile"
      class="topbar-mobile-search"
      :aria-label="$t('topbar.search.click_to_search')"
      @click="openSearch"
    >
      <Search theme="outline" size="18" />
      <span class="topbar-mobile-search-text">{{ $t('topbar.search.click_to_search') }}</span>
    </button>

    <!-- Right side actions -->
    <div class="topbar-right">
      <ab-status-bar
        :items="items"
        :running="running"
        @click-add="() => (showAddRSS = true)"
        @change-lang="changeLocale"
      />
    </div>

    <ab-change-account v-model:show="showAccount"></ab-change-account>
    <ab-add-rss
      v-model:show="showAddRSS"
      v-model:rule="rssRule"
    ></ab-add-rss>
  </div>
</template>

<style lang="scss" scoped>
.topbar {
  display: flex;
  align-items: center;
  gap: 8px;
  height: var(--topbar-height);
  padding: 0 8px;

  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  transition: background-color var(--transition-normal),
              border-color var(--transition-normal),
              box-shadow var(--transition-normal);

  @include forTablet {
    gap: 12px;
    padding: 0 12px;
  }

  @include forDesktop {
    gap: 16px;
    padding: 0 20px;
    border-radius: var(--radius-lg);
  }
}

.topbar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;

  @include forTablet {
    gap: 10px;
  }
}

.topbar-logo {
  width: 20px;
  height: 20px;

  @include forDesktop {
    width: 24px;
    height: 24px;
  }
}

.topbar-wordmark {
  height: 16px;
  position: relative;

  @include forDesktop {
    height: 20px;
  }
}

.topbar-search {
  display: none;

  @include forTablet {
    display: block;
    flex: 1;
    max-width: 400px;
  }
}

.topbar-mobile-search {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  height: 34px;
  padding: 0 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-surface-hover);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: color var(--transition-fast),
              border-color var(--transition-fast),
              background-color var(--transition-fast);

  &:hover {
    color: var(--color-primary);
    border-color: var(--color-primary);
    background: var(--color-primary-light);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }
}

.topbar-mobile-search-text {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.topbar-right {
  flex-shrink: 0;
}

.topbar-right {
  margin-left: auto;
}
</style>
