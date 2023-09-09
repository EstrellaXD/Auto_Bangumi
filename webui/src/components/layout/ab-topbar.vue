<script lang="ts" setup>
import {
  Format,
  Me,
  Pause,
  PlayOne,
  Power,
  Refresh,
} from '@icon-park/vue-next';
import type {BangumiRule} from "#/bangumi";

const {t, changeLocale} = useMyI18n();
const {running, onUpdate, offUpdate} = useAppInfo();

const showAccount = ref(false);
const showAdd = ref(false);
const searchRule = ref<BangumiRule>()

const {start, pause, shutdown, restart, resetRule} = useProgramStore();

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
    label: () => t('topbar.reset_rule'),
    icon: Format,
    handle: resetRule,
  },
  {
    id: 6,
    label: () => t('topbar.profile.title'),
    icon: Me,
    handle: () => {
      showAccount.value = true;
    },
  },
];

const onSearchFocus = ref(false);

function addSearchResult(bangumi: BangumiRule) {
  showAdd.value = true;
  searchRule.value = bangumi;
  console.log('searchRule', searchRule.value);
}

onBeforeMount(() => {
  onUpdate();
});

onUnmounted(() => {
  offUpdate();
});
</script>

<template>
  <div h-60px bg-theme-row text-white rounded-16px fx-cer px-24px>
    <div flex space-x-16px>
      <div fx-cer space-x-16px>
        <img src="/images/logo-light.svg" alt="favicon" wh-24px/>
        <img v-show="onSearchFocus === false" src="/images/AutoBangumi.svg" alt="AutoBangumi" h-24px rel top-2px/>
      </div>

      <ab-search-bar @add-bangumi="addSearchResult"/>
    </div>

    <div ml-auto>
      <ab-status-bar
          :items="items"
          :running="running"
          @click-add="() => (showAdd = true)"
          @change-lang="() => changeLocale()"
      ></ab-status-bar>
    </div>

    <ab-change-account v-model:show="showAccount"></ab-change-account>

    <ab-add-bangumi v-model:show="showAdd" v-model:searchRule="searchRule"></ab-add-bangumi>
  </div>
</template>
