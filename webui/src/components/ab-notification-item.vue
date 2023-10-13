<script lang="ts" setup>
import { NThing } from 'naive-ui';
import type { NotificationData } from '#/notification';

const props = defineProps<NotificationData>();
</script>

<template>
  <NThing :title="props.title" :title-extra="props.datetime" py-2>
    {{ props.content }}
  </NThing>
</template>
