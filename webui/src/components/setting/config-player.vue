<script lang="ts" setup>
const { types, type, rawUrl } = storeToRefs(usePlayerStore());
</script>

<template>
  <ab-fold-panel :title="$t('config.media_player_set.title')">
    <div space-y-8>
      <ab-setting
        v-model:data="type"
        type="select"
        :label="$t('config.media_player_set.type')"
        :prop="{ items: types }"
      ></ab-setting>

      <ab-setting
        v-model:data="rawUrl"
        type="input"
        :label="$t('config.media_player_set.url')"
        :prop="{ placeholder: 'http://192.168.1.100:8096' }"
      ></ab-setting>
    </div>
  </ab-fold-panel>
</template>
