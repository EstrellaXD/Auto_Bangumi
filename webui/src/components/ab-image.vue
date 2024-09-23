<script lang="ts" setup>
import { ErrorPicture } from '@icon-park/vue-next';

withDefaults(
  defineProps<{
    src?: string | null;
    aspectRatio?: number;
    objectFit?: 'fill' | 'contain' | 'cover' | 'none' | 'scale-down';
  }>(),
  {
    objectFit: 'cover',
  }
);
</script>

<template>
  <div rel>
    <template v-if="aspectRatio">
      <div
        w-full
        :style="{ paddingBottom: `calc(${1 / aspectRatio} * 100%)` }"
      ></div>

      <img
        v-if="src"
        :src="src"
        alt="poster"
        abs
        top-0
        left-0
        :style="{ objectFit }"
        wh-full
      />
    </template>

    <template v-else>
      <img v-if="src" :src="src" alt="poster" :style="{ objectFit }" wh-full />

      <div v-else wh-full f-cer border="1 white">
        <ErrorPicture theme="outline" size="24" fill="#333" />
      </div>
    </template>
  </div>
</template>

<style lang="scss" scope></style>
