<script lang="ts" setup>
import {
  MenuUnfold,
  Home,
  Calendar,
  Play,
  Download,
  Log,
  Setting,
  Logout,
} from '@icon-park/vue-next';

const props = withDefaults(
  defineProps<{
    open?: boolean;
  }>(),
  {
    open: false,
  }
);

const show = ref(props.open);
const toggle = () => (show.value = !show.value);

const items = [
  {
    id: 1,
    icon: Home,
    label: 'HomePage',
  },
  {
    id: 2,
    icon: Calendar,
    label: 'Calendar',
  },
  {
    id: 3,
    icon: Play,
    label: 'Player',
  },
  {
    id: 4,
    icon: Download,
    label: 'Downloader',
  },
  {
    id: 5,
    icon: Log,
    label: 'Log',
  },
  {
    id: 6,
    icon: Setting,
    label: 'Setting',
  },
  {
    id: 7,
    icon: Logout,
    label: 'Logout',
  },
];
</script>

<template>
  <div
    :class="[show ? 'w-240px' : 'w-72px']"
    bg-theme-col
    rounded-12px
    text-white
    overflow-hidden
    transition-width
    flex="~ col"
    pb-12px
  >
    <div
      @click="toggle"
      w-full
      h-60px
      is-btn
      f-cer
      bg="#E7E7E7"
      text="#2A1C52"
      rel
    >
      <div :class="[!show && 'abs opacity-0']" transition-opacity>
        <div text-h1>Menu</div>
      </div>

      <menu-unfold
        theme="outline"
        size="24"
        fill="#2A1C52"
        abs
        left="24px"
        :class="[show && 'rotate-y-180']"
      />
    </div>

    <template v-for="i in items" :key="i.id">
      <div
        :class="[i.label === 'Logout' && 'mt-auto']"
        :title="i.label"
        fx-cer
        px-24px
        space-x-42px
        h-48px
        is-btn
        transition-colors
        hover:bg="#F1F5FA"
        hover:text="#2A1C52"
      >
        <component :is="i.icon" :size="24" />
        <div text-h2>{{ i.label }}</div>
      </div>
    </template>
  </div>
</template>
