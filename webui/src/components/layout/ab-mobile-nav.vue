<script lang="ts" setup>
import {
  Calendar,
  Download,
  Home,
  Log,
  Moon,
  SettingTwo,
  Sun,
} from '@icon-park/vue-next';
import InlineSvg from 'vue-inline-svg';

const { t } = useMyI18n();
const route = useRoute();
const { isDark, toggle: toggleDark } = useDarkMode();

const RSS = h(
  'span',
  { style: { display: 'flex', alignItems: 'center', justifyContent: 'center', width: '20px', height: '20px' } },
  h(InlineSvg, { src: './images/RSS.svg', width: '14', height: '14' })
);

const navItems = [
  { id: 1, icon: Home, label: () => t('sidebar.homepage'), path: '/bangumi' },
  { id: 2, icon: Calendar, label: () => t('sidebar.calendar'), path: '/calendar' },
  { id: 3, icon: RSS, label: () => t('sidebar.rss'), path: '/rss' },
  { id: 5, icon: Download, label: () => t('sidebar.downloader'), path: '/downloader',
    hidden: localStorage.getItem('enable_downloader_iframe') !== '1' },
  { id: 6, icon: Log, label: () => t('sidebar.log'), path: '/log' },
  { id: 7, icon: SettingTwo, label: () => t('sidebar.config'), path: '/config' },
];

const visibleItems = computed(() => navItems.filter((i) => !i.hidden));
</script>

<template>
  <nav class="mobile-nav" role="navigation" aria-label="Main navigation">
    <RouterLink
      v-for="item in visibleItems"
      :key="item.id"
      :to="item.path"
      replace
      class="mobile-nav__item"
      :class="{ 'mobile-nav__item--active': route.path === item.path }"
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
      <span class="mobile-nav__label">{{ isDark ? 'Light' : 'Dark' }}</span>
    </button>
  </nav>
</template>

<style lang="scss" scoped>
.mobile-nav {
  display: flex;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow-x: auto;
  scrollbar-width: none;
  @include safeAreaBottom(padding-bottom);

  &::-webkit-scrollbar {
    display: none;
  }

  &__item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    min-width: 0;
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
    max-width: 100%;
    line-height: 1.2;
  }
}
</style>
