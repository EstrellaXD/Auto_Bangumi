<script lang="ts" setup>
import { NThing } from 'naive-ui';
import type { Notification } from '#/notification';

const props = defineProps<Notification>();
</script>

<template>
  <NThing :title="props.title" :title-extra="props.datetime" py-2>
    {{ props.content }}
  </NThing>
</template>
