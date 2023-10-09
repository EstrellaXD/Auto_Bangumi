<script lang="ts" setup>
import { NBadge, NIcon } from 'naive-ui';
import { Remind } from '@icon-park/vue-next';

// TODO: use watchEffect to subscribe topic and update messageCount
const messageCount = ref(1);
</script>

<template>
  <NBadge :value="messageCount" :max="99">
    <NIcon depth="1" size="24" color="white" is-btn btn-click>
      <Remind theme="outline" />
    </NIcon>
  </NBadge>
</template>
