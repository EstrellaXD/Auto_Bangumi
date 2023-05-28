<script lang="ts" setup>
const { types, type, url } = storeToRefs(usePlayerStore());
</script>

<template>
  <ab-fold-panel title="Media Player Setting">
    <div space-y-12px>
      <ab-setting
        type="select"
        label="type"
        v-model:data="type"
        :prop="{ items: types }"
      ></ab-setting>

      <ab-setting
        type="input"
        label="url"
        :prop="{ placeholder: 'media player url' }"
        v-model:data="url"
      ></ab-setting>
    </div>
  </ab-fold-panel>
</template>
