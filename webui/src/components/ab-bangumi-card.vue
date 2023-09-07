<script lang="ts" setup>
import {ErrorPicture, Write} from '@icon-park/vue-next';
import type {BangumiRule} from "#/bangumi";

withDefaults(
    defineProps<{
      type?: 'primary' | 'search' | 'mobile';
      bangumi: BangumiRule;
    }>(),
    {
      type: 'primary',
    }
);

defineEmits(['click']);
</script>

<template>
  <div v-if="type === 'primary'" w-150px is-btn @click="() => $emit('click')">
    <div rounded-4px overflow-hidden poster-shandow rel>
      <div w-full h-210px>
        <template v-if="bangumi.poster_link">
          <img :src="bangumi.poster_link" alt="poster" wh-full/>
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

    <div py-4px>
      <div text-h3 truncate>{{ bangumi.official_title }}</div>
      <ab-tag
          :title="`Season ${bangumi.season}`"
          type="primary"
      />
    </div>
  </div>
  <div v-else-if="type === 'search'" w-480px rounded-12px p-4px shadow class="card-border">
    <div
        bg-white rounded-8px p-12px
        fx-cer justify-between
        space-x-16px>
      <div w-400px space-x-16px fx-cer>
        <div h-44px w-72px rounded-6px overflow-hidden>
          <template v-if="bangumi.poster_link">
            <img :src="bangumi.poster_link" alt="poster" w-full class="search-image"/>
          </template>

          <template v-else>
            <div wh-full f-cer border="1 white">
              <ErrorPicture theme="outline" size="24" fill="#333"/>
            </div>
          </template>
        </div>
        <div flex-col space-y-4px>
          <div w-300px text-h3 text-primary truncate>{{ bangumi.official_title }}</div>
          <div flex space-x-8px>
            <ab-tag
                :title="`Season ${bangumi.season}`"
                type="primary"
            />
            <ab-tag
                v-if="bangumi.group_name !== ''"
                :title="bangumi.group_name"
                type="primary"
            />
            <ab-tag
                v-if="bangumi.dpi"
                :title="bangumi.dpi"
                type="primary"
            />
            <ab-tag
                v-if="bangumi.subtitle"
                :title="bangumi.subtitle"
                type="primary"
            />
          </div>
        </div>
      </div>
      <ab-add :round="true" type="medium" @click="()=> $emit('click')"/>
    </div>
  </div>
</template>

<style>
.card-border {
  background: #EEE5F4;
}


.search-image {
  transform: translateY(-25%);
}
</style>