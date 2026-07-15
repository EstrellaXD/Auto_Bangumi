<script lang="ts" setup>
import { Home, More, Search } from '@icon-park/vue-next';
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import AbMobileMoreSheet from './ab-mobile-more-sheet.vue';
import { useMyI18n } from '@/hooks/useMyI18n';
import { useMobileShellStore } from '@/store/mobile-shell';
import { getMobileNavDestination } from '@/utils/mobile-navigation';

const { t } = useMyI18n();
const route = useRoute();
const mobileShell = useMobileShellStore();

const moreOpen = computed(() => mobileShell.activeOverlay === 'more');
const activeDestination = computed(() =>
  moreOpen.value ? 'more' : getMobileNavDestination(route.path)
);

function closeMore() {
  mobileShell.closeOverlay('more');
}

function toggleMore() {
  if (moreOpen.value) {
    closeMore();
  } else {
    mobileShell.openOverlay('more');
  }
}
</script>

<template>
  <nav class="mobile-nav" :aria-label="t('mobile.navigation')">
    <RouterLink
      to="/home"
      class="mobile-nav__item"
      :class="{ 'mobile-nav__item--active': activeDestination === 'home' }"
      :aria-current="activeDestination === 'home' ? 'page' : undefined"
      @click="closeMore"
    >
      <Home :size="20" class="mobile-nav__icon" aria-hidden="true" />
      <span class="mobile-nav__label">{{ t('mobile.home') }}</span>
    </RouterLink>

    <RouterLink
      to="/search"
      class="mobile-nav__item"
      :class="{ 'mobile-nav__item--active': activeDestination === 'search' }"
      :aria-current="activeDestination === 'search' ? 'page' : undefined"
      @click="closeMore"
    >
      <Search :size="20" class="mobile-nav__icon" aria-hidden="true" />
      <span class="mobile-nav__label">{{ t('mobile.search') }}</span>
    </RouterLink>

    <button
      type="button"
      class="mobile-nav__item"
      :class="{ 'mobile-nav__item--active': activeDestination === 'more' }"
      :aria-label="t('common.moreActions')"
      aria-haspopup="dialog"
      :aria-expanded="moreOpen"
      @click="toggleMore"
    >
      <More :size="20" class="mobile-nav__icon" aria-hidden="true" />
      <span class="mobile-nav__label">{{ t('mobile.more') }}</span>
    </button>
  </nav>

  <AbMobileMoreSheet :show="moreOpen" @update:show="closeMore" />
</template>

<style lang="scss" scoped>
.mobile-nav {
  position: fixed;
  left: calc(var(--layout-padding) + env(safe-area-inset-left, 0px));
  right: calc(var(--layout-padding) + env(safe-area-inset-right, 0px));
  bottom: var(--layout-padding);
  z-index: var(--z-fixed);
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
  @include safeAreaBottom(padding-bottom);
}

.mobile-nav__item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  min-width: 0;
  min-height: 56px;
  padding: 6px 4px;
  color: var(--color-text-secondary);
  background: transparent;
  border: 0;
  border-radius: var(--radius-md);
  cursor: pointer;
  font: inherit;
  text-decoration: none;
  user-select: none;
  transition: color var(--transition-fast),
    background-color var(--transition-fast);

  &:hover,
  &:focus-visible {
    color: var(--color-primary);
    background: var(--color-primary-light);
  }

  &--active {
    color: var(--color-primary);
    font-weight: 600;

    &::after {
      content: '';
      position: absolute;
      top: 4px;
      left: 50%;
      width: 22px;
      height: 3px;
      border-radius: var(--radius-full);
      background: var(--color-primary);
      transform: translateX(-50%);
    }
  }
}

.mobile-nav__icon {
  flex: 0 0 auto;
}

.mobile-nav__label {
  max-width: 100%;
  overflow: hidden;
  font-size: 12px;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
