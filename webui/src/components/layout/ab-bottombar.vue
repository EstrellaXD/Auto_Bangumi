<script lang="ts" setup>
import {
  Home,
  Log,
  Search,
  SettingTwo,
} from '@icon-park/vue-next';
import InlineSvg from "vue-inline-svg";

const props = withDefaults(
    defineProps<{
      open?: boolean;
    }>(),
    {
      open: false,
    }
);

const show = ref(props.open);
const route = useRoute();

const RSS = h(
    'span',
    {class: ['rel', 'left-2px']},
    h(InlineSvg, {src: '/images/RSS.svg'})
);

const items1 = [
  {
    id: 1,
    icon: Home,
    path: '/bangumi',
  },
  {
    id: 2,
    icon: RSS,
    path: '/rss',
  },
]

const items2 = [
  {
    id: 3,
    icon: Log,
    path: '/log',
  },
  {
    id: 4,
    icon: SettingTwo,
    path: '/config',
  },
]
</script>

<template>
  <div>
    <div flex w-full justify-between class="bottom-bar">
      <RouterLink
          v-for="i in items1"
          :key="i.id"
          :to="i.path"
          f-cer
          h-56px
          w-full
          is-btn
          bg-white
          shadow="primary"
          :class="[
          route.path === i.path && 'bg-theme-row text-white rounded-8px',
        ]"
      >
        <Component :is="i.icon" size="24px"/>
      </RouterLink>
      <div f-cer bg-white shadow-primary class="search-outside">
        <div f-cer wh-60px rounded-30px bg-theme-row>
          <div f-cer wh-54px rounded-30px bg-white>
            <div wh-48px f-cer rounded-24px bg-theme-row text-white shadow-primary>
              <Component :is="Search" size="24px"/>
            </div>
          </div>
        </div>
      </div>
      <RouterLink
          v-for="i in items2"
          :key="i.id"
          :to="i.path"
          f-cer
          h-56px
          bg-white
          w-full
          is-btn
          shadow="primary"
          :class="[
          route.path === i.path && 'rounded-8px bg-theme-row text-white',
        ]"
      >
        <Component :is="i.icon" size="24px"/>
      </RouterLink>
    </div>
  </div>
</template>


<style lang="scss">
.bottom-bar {
  display: flex;
  align-items: flex-end;
  align-self: stretch;
}

.search-outside {
  display: flex;
  padding: 8px 8px 24px 8px;
  align-items: flex-start;
  gap: 8px;
  border-radius: 40px 40px 0 0;
}
</style>

