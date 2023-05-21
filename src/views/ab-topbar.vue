<script lang="ts" setup>
import { PlayOne, Pause, Refresh, Power, Me } from '@icon-park/vue-next';

const search = ref('');

const { onUpdate } = programStore();
const { running } = storeToRefs(programStore());

const items = [
  {
    id: 1,
    label: 'Start',
    icon: PlayOne,
  },
  {
    id: 2,
    label: 'Pause',
    icon: Pause,
  },
  {
    id: 3,
    label: 'Restart',
    icon: Refresh,
  },
  {
    id: 4,
    label: 'Shutdown',
    icon: Power,
  },
  {
    id: 5,
    label: 'Profile',
    icon: Me,
  },
];

onBeforeMount(() => onUpdate());
</script>

<template>
  <div h-60px bg-theme-row text-white rounded-12px fx-cer px-24px>
    <div text-h1 mr-12px>AutoBangumi</div>

    <ab-search v-model:value="search" />

    <div ml-auto>
      <ab-status-bar :items="items" :running="running"></ab-status-bar>
    </div>
  </div>
</template>

<style lang="scss" scope></style>
