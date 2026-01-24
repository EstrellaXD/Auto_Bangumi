<script lang="tsx" setup>
import {
  Calendar,
  Download,
  Home,
  Log,
  Logout,
  MenuUnfold,
  Moon,
  Play,
  SettingTwo,
  Sun,
} from '@icon-park/vue-next';
import InlineSvg from 'vue-inline-svg';

const props = withDefaults(
  defineProps<{
    open?: boolean;
  }>(),
  {
    open: false,
  }
);

const { t } = useMyI18n();
const { logout } = useAuth();
const route = useRoute();
const { isMobile, isTablet, isMobileOrTablet } = useBreakpointQuery();
const { isDark, toggle: toggleDark } = useDarkMode();

const show = ref(props.open);
const toggle = () => (show.value = !show.value);

const RSS = h(
  'span',
  { style: { display: 'flex', alignItems: 'center', justifyContent: 'center', width: '20px', height: '20px' } },
  h(InlineSvg, { src: './images/RSS.svg', width: '16', height: '16' })
);

const items = [
  {
    id: 1,
    icon: Home,
    label: () => t('sidebar.homepage'),
    path: '/bangumi',
  },
  {
    id: 2,
    icon: Calendar,
    label: () => t('sidebar.calendar'),
    path: '/calendar',
  },
  {
    id: 3,
    icon: RSS,
    label: () => t('sidebar.rss'),
    path: '/rss',
  },
  {
    id: 4,
    icon: Play,
    label: () => t('sidebar.player'),
    path: '/player',
  },
  {
    id: 5,
    icon: Download,
    label: () => t('sidebar.downloader'),
    path: '/downloader',
    hidden: localStorage.getItem('enable_downloader_iframe') !== '1',
  },
  {
    id: 6,
    icon: Log,
    label: () => t('sidebar.log'),
    path: '/log',
  },
  {
    id: 7,
    icon: SettingTwo,
    label: () => t('sidebar.config'),
    path: '/config',
  },
];

function Exit() {
  return (
    <div
      title="logout"
      class={[
        'sidebar-item sidebar-item--action',
        isMobileOrTablet.value ? 'h-40' : '',
      ]}
      onClick={logout}
    >
      <Logout size={20} />
      {!isMobileOrTablet.value && show.value && <div class="sidebar-item-label">{t('sidebar.logout')}</div>}
    </div>
  );
}
</script>

<template>
  <media-query>
    <div
      class="sidebar"
      :class="[show ? 'sidebar--expanded' : 'sidebar--collapsed']"
    >
      <div class="sidebar-inner">
        <!-- Toggle header -->
        <button
          class="sidebar-header"
          :aria-label="show ? 'Collapse sidebar' : 'Expand sidebar'"
          :aria-expanded="show"
          @click="toggle"
        >
          <div v-show="show" class="sidebar-title">
            {{ $t('sidebar.title') }}
          </div>
          <MenuUnfold
            theme="outline"
            size="20"
            class="sidebar-toggle-icon"
            :class="[show && 'sidebar-toggle-icon--open']"
          />
        </button>

        <!-- Navigation -->
        <nav class="sidebar-nav">
          <RouterLink
            v-for="i in items"
            :key="i.id"
            :to="i.path"
            replace
            :title="i.label()"
            class="sidebar-item"
            :class="[
              route.path === i.path && 'sidebar-item--active',
              i.hidden && 'hidden',
            ]"
          >
            <Component :is="i.icon" :size="20" />
            <div v-show="show" class="sidebar-item-label">{{ i.label() }}</div>
          </RouterLink>
        </nav>

        <!-- Bottom actions -->
        <div class="sidebar-footer">
          <button
            class="sidebar-item sidebar-item--action sidebar-item--theme"
            :title="isDark ? 'Light mode' : 'Dark mode'"
            :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
            @click="toggleDark"
          >
            <Moon v-if="!isDark" :size="20" />
            <Sun v-else :size="20" />
            <div v-show="show" class="sidebar-item-label">
              {{ isDark ? 'Light' : 'Dark' }}
            </div>
          </button>
          <Exit />
        </div>
      </div>
    </div>

    <!-- Tablet: mini sidebar (icons only, no toggle) -->
    <template #tablet>
      <div class="sidebar sidebar--collapsed sidebar--tablet">
        <div class="sidebar-inner">
          <nav class="sidebar-nav">
            <RouterLink
              v-for="i in items"
              :key="i.id"
              :to="i.path"
              replace
              :title="i.label()"
              class="sidebar-item"
              :class="[
                route.path === i.path && 'sidebar-item--active',
                i.hidden && 'hidden',
              ]"
            >
              <Component :is="i.icon" :size="20" />
            </RouterLink>
          </nav>

          <div class="sidebar-footer">
            <button
              class="sidebar-item sidebar-item--action sidebar-item--theme"
              :title="isDark ? 'Light mode' : 'Dark mode'"
              @click="toggleDark"
            >
              <Moon v-if="!isDark" :size="20" />
              <Sun v-else :size="20" />
            </button>
            <Exit />
          </div>
        </div>
      </div>
    </template>

    <!-- Mobile: enhanced bottom navigation with labels -->
    <template #mobile>
      <ab-mobile-nav />
    </template>
  </media-query>
</template>

<style lang="scss" scoped>
.sidebar {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: width var(--transition-normal),
              background-color var(--transition-normal),
              border-color var(--transition-normal);
  overflow: hidden;

  &--expanded {
    width: 200px;
  }

  &--collapsed {
    width: 64px;
  }
}

.sidebar-inner {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 52px;
  padding: 0 20px;
  cursor: pointer;
  position: relative;
  border: none;
  border-bottom: 1px solid var(--color-border);
  background: transparent;
  transition: border-color var(--transition-normal),
              background-color var(--transition-fast);

  &:hover {
    background: var(--color-surface-hover);
  }
}

.sidebar-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  transition: opacity var(--transition-fast);
}

.sidebar-toggle-icon {
  position: absolute;
  left: 20px;
  color: var(--color-text-secondary);
  transition: transform var(--transition-normal);

  &--open {
    transform: rotateY(180deg);
  }
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  padding: 8px;
  gap: 2px;
  flex: 1;
  overflow-y: auto;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  cursor: pointer;
  user-select: none;
  color: var(--color-text-secondary);
  transition: color var(--transition-fast),
              background-color var(--transition-fast);
  white-space: nowrap;

  &:hover {
    color: var(--color-primary);
    background: var(--color-primary-light);
  }

  &--active {
    color: var(--color-primary);
    background: var(--color-primary-light);
    font-weight: 500;
  }

  &--action {
    color: var(--color-text-muted);
    border: none;
    background: transparent;
    width: 100%;
    font: inherit;

    &:hover {
      color: var(--color-danger);
      background: rgba(239, 68, 68, 0.08);
    }
  }

  &--theme:hover {
    color: var(--color-primary);
    background: var(--color-primary-light);
  }
}

.sidebar-item-label {
  font-size: 14px;
}

.sidebar-footer {
  display: flex;
  flex-direction: column;
  padding: 8px;
  gap: 2px;
  border-top: 1px solid var(--color-border);
  margin-top: auto;
  transition: border-color var(--transition-normal);
}

// Tablet: fixed mini sidebar
.sidebar--tablet {
  width: 56px;

  .sidebar-nav {
    padding: 4px;
  }

  .sidebar-item {
    justify-content: center;
    padding: 10px;
  }

  .sidebar-footer {
    padding: 4px;
  }
}
</style>
