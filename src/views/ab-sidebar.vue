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
const route = useRoute();

const items = [
  {
    id: 1,
    icon: Home,
    label: 'HomePage',
    path: '/',
  },
  {
    id: 2,
    icon: Calendar,
    label: 'Calendar',
    path: '/calendar',
    hidden: true,
  },
  {
    id: 3,
    icon: Play,
    label: 'Player',
    path: '/player',
  },
  {
    id: 4,
    icon: Download,
    label: 'Downloader',
    path: '/downloader',
  },
  {
    id: 5,
    icon: Log,
    label: 'Log',
    path: '/log',
  },
  {
    id: 6,
    icon: Setting,
    label: 'Config',
    path: '/config',
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

    <template v-for="i in items">
      <RouterLink
        :to="i.path"
        replace
        :title="i.label"
        fx-cer
        px-24px
        space-x-42px
        h-48px
        is-btn
        transition-colors
        hover:bg="#F1F5FA"
        hover:text="#2A1C52"
        :class="[
          route.path === i.path && 'bg-[#F1F5FA] text-[#2A1C52]',
          i.hidden && 'hidden',
        ]"
      >
        <Component :is="i.icon" :size="24" />
        <div text-h2>{{ i.label }}</div>
      </RouterLink>
    </template>

    <div
      title="logout"
      mt-auto
      fx-cer
      px-24px
      space-x-42px
      h-48px
      is-btn
      transition-colors
      hover:bg="#F1F5FA"
      hover:text="#2A1C52"
    >
      <Logout :size="24" />
      <div text-h2>Logout</div>
    </div>
  </div>
</template>
