<script lang="ts" setup>
import { Write } from '@icon-park/vue-next';

withDefaults(
  defineProps<{
    poster: string;
    name: string;
    season: number;
  }>(),
  {}
);

defineEmits(['click']);
</script>

<template>
  <div w-150px is-btn @click="() => $emit('click')">
    <div rounded-4px overflow-hidden poster-shandow rel>
      <img :src="`https://mikanani.me${poster}`" alt="poster" w-full h-210px />

      <div
        abs
        f-cer
        z-1
        inset-0
        opacity-0
        transition-all
        duration-300
        hover:backdrop-blur-2px
        hover:bg-white
        hover:bg-opacity-30
        hover:opacity-100
        active:duration-0
        active:bg-opacity-60
        class="group"
      >
        <div
          text-white
          rounded="1/2"
          wh-44px
          f-cer
          bg-theme-row
          class="group-active:poster-pen-active"
        >
          <Write size="20" />
        </div>
      </div>
    </div>

    <div px-4px py-8px>
      <div text-h3>{{ name }}</div>
      <div text-main>Season {{ season }}</div>
    </div>
  </div>
</template>
