<script lang="ts" setup>
import {
  AppStore,
  Calendar,
  Download,
  Home,
  Log,
  Moon,
  Puzzle,
  SettingTwo,
  Sun,
} from '@icon-park/vue-next';
import InlineSvg from 'vue-inline-svg';
import { slotTitle, usePluginPages } from '@/hooks/usePluginUi';

const { t, lang } = useMyI18n();
const route = useRoute();
const { isDark, toggle: toggleDark } = useDarkMode();

const RSS = h(
  'span',
  {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '20px',
      height: '20px',
    },
  },
  h(InlineSvg, { src: './images/RSS.svg', width: '14', height: '14' })
);

const navItems = [
  { id: 1, icon: Home, label: () => t('sidebar.homepage'), path: '/bangumi' },
  {
    id: 2,
    icon: Calendar,
    label: () => t('sidebar.calendar'),
    path: '/calendar',
  },
  { id: 3, icon: RSS, label: () => t('sidebar.rss'), path: '/rss' },
  {
    id: 5,
    icon: Download,
    label: () => t('sidebar.downloader'),
    path: '/downloader',
    hidden: localStorage.getItem('enable_downloader_iframe') !== '1',
  },
  { id: 6, icon: Log, label: () => t('sidebar.log'), path: '/log' },
  {
    id: 8,
    icon: AppStore,
    label: () => t('sidebar.market_short'),
    path: '/market',
  },
  {
    id: 7,
    icon: SettingTwo,
    label: () => t('sidebar.config'),
    path: '/config',
  },
];

// 插件经 page 挂载点提供的页面，排在设置之前；导航栏可横向滚动
const pageSlots = usePluginPages();
const visibleItems = computed(() => {
  const pluginItems = pageSlots.value.map((ui, index) => ({
    id: 100 + index,
    icon: Puzzle,
    label: () => slotTitle(ui, lang.value === 'zh-CN' ? 'zh-CN' : 'en-US'),
    path: `/plugins/${encodeURIComponent(ui.plugin_id)}`,
  }));
  const shown = navItems.filter((i) => !i.hidden);
  return [...shown.slice(0, -1), ...pluginItems, shown[shown.length - 1]];
});
</script>

<template>
  <nav class="mobile-nav" role="navigation" aria-label="Main navigation">
    <RouterLink
      v-for="item in visibleItems"
      :key="item.id"
      :to="item.path"
      replace
      class="mobile-nav__item"
      :class="{
        'mobile-nav__item--active':
          route.path === item.path || route.path.startsWith(`${item.path}/`),
      }"
      :aria-label="item.label()"
    >
      <Component :is="item.icon" :size="18" class="mobile-nav__icon" />
      <span class="mobile-nav__label">{{ item.label() }}</span>
    </RouterLink>

    <button
      class="mobile-nav__item"
      :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
      @click="toggleDark"
    >
      <Moon v-if="!isDark" :size="18" class="mobile-nav__icon" />
      <Sun v-else :size="18" class="mobile-nav__icon" />
      <span class="mobile-nav__label">{{
        isDark ? t('theme.light') : t('theme.dark')
      }}</span>
    </button>
  </nav>
</template>

<style lang="scss" scoped>
.mobile-nav {
  // Thumb-reachable bottom bar. The nav is rendered inside .layout-main,
  // which would otherwise place it at the top of the content column.
  position: fixed;
  left: var(--layout-padding);
  right: var(--layout-padding);
  bottom: var(--layout-padding);
  z-index: var(--z-fixed);
  display: flex;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow-x: auto;
  scrollbar-width: none;
  @include safeAreaBottom(padding-bottom);

  &::-webkit-scrollbar {
    display: none;
  }

  &__item {
    // 不收缩：项多时导航栏横向滚动，保持 44px 以上的触控区域
    flex: 1 0 auto;
    min-width: 56px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    height: 56px;
    padding: 6px 4px;
    cursor: pointer;
    user-select: none;
    color: var(--color-text-muted);
    background: transparent;
    border: none;
    border-radius: var(--radius-md);
    transition: color var(--transition-fast),
      background-color var(--transition-fast);
    text-decoration: none;
    font: inherit;
    position: relative;

    &:active {
      transform: scale(0.95);
    }

    &--active {
      color: var(--color-primary);

      &::after {
        content: '';
        position: absolute;
        top: 4px;
        left: 50%;
        transform: translateX(-50%);
        width: 20px;
        height: 3px;
        border-radius: var(--radius-full);
        background: var(--color-primary);
      }
    }
  }

  &__icon {
    flex-shrink: 0;
  }

  &__label {
    font-size: 11px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 6em;
    line-height: 1.2;
  }
}
</style>
