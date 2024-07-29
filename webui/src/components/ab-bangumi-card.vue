<script lang="ts" setup>
import { Write } from '@icon-park/vue-next';
import type { BangumiRule } from '#/bangumi';

withDefaults(
  defineProps<{
    type?: 'primary' | 'search';
    bangumi: BangumiRule;
  }>(),
  {
    type: 'primary',
  }
);

defineEmits(['click']);
</script>

<template>
  <template v-if="type === 'primary'">
    <div w="full pc:150" is-btn @click="() => $emit('click')">
      <div rounded-4 overflow-hidden poster-shandow rel>
        <ab-image
          :src="bangumi.poster_link"
          :aspect-ratio="1 / 1.5"
          w-full
        ></ab-image>

        <div
          abs
          f-cer
          z-1
          inset-0
          opacity-0
          transition="all duration-300"
          hover="backdrop-blur-2 bg-white bg-opacity-30 opacity-100"
          active="duration-0 bg-opacity-60"
          class="group"
        >
          <div
            text-white
            rounded="1/2"
            wh-44
            f-cer
            bg-theme-row
            group-active="poster-pen-active"
          >
            <Write size="20" />
          </div>
        </div>
      </div>

      <div py-4>
        <div text-h3 truncate>{{ bangumi.official_title }}</div>

        <div flex="~ wrap col" pc:flex-row gap-5>
          <template v-for="i in ['season', 'group_name']" :key="i">
            <ab-tag
              v-if="bangumi[i]"
              :title="i === 'season' ? `Season ${bangumi[i]}` : bangumi[i]"
              type="primary"
              pc:max-w="1/2"
            />
          </template>
        </div>
      </div>
    </div>
  </template>

  <template v-else-if="type === 'search'">
    <div
      w-480
      rounded-12
      p-4
      shadow
      bg="#eee5f4"
      transition="opacity ease-in-out duration-300"
    >
      <div bg-white rounded-8 p-12 fx-cer justify-between gap-x-16>
        <div w-400 gap-x-16 fx-cer>
          <div w-72 rounded-6 overflow-hidden>
            <ab-image
              :src="bangumi.poster_link"
              :aspect-ratio="72 / 44"
              w-full
            ></ab-image>
          </div>

          <div flex="~ col gap-y-4">
            <div w-300 text="h3 primary" truncate>
              {{ bangumi.official_title }}
            </div>
            <div flex="~ gap-x-8">
              <template
                v-for="i in ['season', 'group_name', 'subtitle']"
                :key="i"
              >
                <ab-tag
                  v-if="bangumi[i]"
                  :title="i === 'season' ? `Season ${bangumi[i]}` : bangumi[i]"
                  type="primary"
                />
              </template>
            </div>
          </div>
        </div>
        <ab-add :round="true" type="medium" @click="() => $emit('click')" />
      </div>
    </div>
  </template>
</template>
