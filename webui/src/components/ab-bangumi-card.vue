<script lang="ts" setup>
import {ErrorPicture, Write} from '@icon-park/vue-next';

withDefaults(
    defineProps<{
      poster: string;
      name: string;
      season: number;
      group: string;
    }>(),
    {}
);

defineEmits(['click']);
</script>

<template>
  <div w-150px is-btn @click="() => $emit('click')">
    <div rounded-4px overflow-hidden poster-shandow rel>
      <div w-full h-210px>
        <template v-if="poster !== ''">
          <img :src="`https://mikanani.me${poster}`" alt="poster" wh-full/>
        </template>

        <template v-else>
          <div wh-full f-cer border="1 white">
            <ErrorPicture theme="outline" size="24" fill="#333"/>
          </div>
        </template>
      </div>

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
          <Write size="20"/>
        </div>
      </div>
    </div>

    <div px-4px py-4px>
      <div text-h3 truncate>{{ name }}</div>
      <div flex space-x-4px>
        <ab-tag
          :title="`Season ${season}`"
          />
        <ab-tag
          :title="group"
          />
      </div>
    </div>
  </div>
</template>
