<script lang="ts" setup>
import {
  Format,
  Me,
  Pause,
  PlayOne,
  Power,
  Refresh,
} from '@icon-park/vue-next';
import { ruleTemplate } from '#/bangumi';

const { t, changeLocale } = useMyI18n();
const { running, onUpdate, offUpdate } = useAppInfo();

const showAccount = ref(false);
const showAddRSS = ref(false);
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
    <div class="topbar-left">
      <div class="topbar-brand">
        <img
          :src="isDark ? '/images/logo-light.svg' : '/images/logo.svg'"
          alt="favicon"
          class="topbar-logo"
        />
        <img
          v-show="onSearchFocus === false"
          :src="isDark ? '/images/AutoBangumi.svg' : '/images/AutoBangumi-dark.svg'"
          alt="AutoBangumi"
          class="topbar-wordmark"
        />
      </div>

      <div class="topbar-search">
        <ab-search-bar />
      </div>
    </div>

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
  height: var(--topbar-height);
  padding: 0 12px;

  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  transition: background-color var(--transition-normal),
              border-color var(--transition-normal),
              box-shadow var(--transition-normal);

  @include forTablet {
    padding: 0 16px;
  }

  @include forDesktop {
    padding: 0 20px;
    border-radius: var(--radius-lg);
  }
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.topbar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
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
  }
}

.topbar-right {
  margin-left: auto;
}
</style>
