<script lang="ts" setup>
import {
  Calendar,
  Download,
  Home,
  Log,
  Logout,
  MenuUnfold,
  Play,
  SettingTwo,
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

const show = ref(props.open);
const toggle = () => (show.value = !show.value);
const route = useRoute();
const { logout } = useAuth();

const RSS = h(
  'span',
  { class: ['rel', 'left-2px'] },
  h(InlineSvg, { src: './images/RSS.svg' })
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
    hidden: true,
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
</script>

<template>
  <div
    :class="[show ? 'w-240px' : 'w-72px']"
    bg-theme-col
    text-white
    transition-width
    pb-12px
    rounded-16px
  >
    <div overflow-hidden wh-full flex="~ col">
      <div
        w-full
        h-60px
        is-btn
        f-cer
        rounded-t-10px
        bg="#E7E7E7"
        text="#2A1C52"
        rel
        @click="toggle"
      >
        <div :class="[!show && 'abs opacity-0']" transition-opacity>
          <div text-h1>{{ $t('sidebar.title') }}</div>
        </div>

        <MenuUnfold
          theme="outline"
          size="24"
          fill="#2A1C52"
          abs
          left="24px"
          :class="[show && 'rotate-y-180']"
        />
      </div>

      <RouterLink
        v-for="i in items"
        :key="i.id"
        :to="i.path"
        replace
        :title="i.label()"
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

        <div text-h2>{{ i.label() }}</div>
      </RouterLink>

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
        @click="logout"
      >
        <Logout :size="24" />
        <div text-h2>{{ $t('sidebar.logout') }}</div>
      </div>
    </div>
  </div>
</template>
