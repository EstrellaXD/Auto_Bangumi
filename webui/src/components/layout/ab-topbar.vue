<script lang="ts" setup>
import {
  Me,
  Pause,
  PlayOne,
  Power,
  Refresh,
  Format,
} from '@icon-park/vue-next';
import { useI18n } from 'vue-i18n';
const { t, locale } = useI18n({ useScope: 'global' });
const search = ref('');
const show = ref(false);
const showAdd = ref(false);

const { onUpdate, offUpdate, start, pause, shutdown, restart, resetRule } =
  useProgramStore();
const { running } = storeToRefs(useProgramStore());

const items = [
  {
    id: 1,
    label: t('topbar.start'),
    icon: PlayOne,
    handle: start,
  },
  {
    id: 2,
    label: t('topbar.pause'),
    icon: Pause,
    handle: pause,
  },
  {
    id: 3,
    label: t('topbar.restart'),
    icon: Refresh,
    handle: restart,
  },
  {
    id: 4,
    label: t('topbar.shutdown'),
    icon: Power,
    handle: shutdown,
  },
  {
    id: 5,
    label: t('topbar.resetrule'),
    icon: Format,
    handle: resetRule,
  },
  {
    id: 6,
    label: t('topbar.profile.title'),
    icon: Me,
    handle: () => {
      show.value = true;
    },
  },
];

onBeforeMount(() => {
  onUpdate();
});

onUnmounted(() => {
  offUpdate();
});

function changeLocale(){
  if(t.value === 'zh-CN'){
    t.value = locale.value = 'en'
  } else {
    t.value = locale.value = 'zh-CN';
  }
}
</script>

<template>
  <div h-60px bg-theme-row text-white rounded-12px fx-cer px-24px>
    <div fx-cer space-x-16px>
      <img src="/favicon-light.svg" alt="favicon" wh-24px />
      <img src="/AutoBangumi.svg" alt="AutoBangumi" h-24px rel top-2px />
    </div>

    <ab-search v-model:value="search" hidden />

    <div ml-auto>
        <ab-status-bar
        :items="items"
        :running="running"
        @click-add="() => (showAdd = true)"
        @change-lang="() => changeLocale()"
      ></ab-status-bar>
    </div>

    <ab-change-account v-model:show="show"></ab-change-account>

    <ab-add-bangumi v-model:show="showAdd"></ab-add-bangumi>
  </div>
</template>
