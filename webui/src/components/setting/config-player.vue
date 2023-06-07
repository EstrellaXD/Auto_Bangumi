<script lang="ts" setup>
const { types, type, url } = storeToRefs(usePlayerStore());
</script>

<template>
  <ab-fold-panel title="Media Player Setting">
    <div space-y-12px>
      <ab-setting
        v-model:data="type"
        type="select"
        label="type"
        :prop="{ items: types }"
      ></ab-setting>

      <ab-setting
        v-model:data="url"
        type="input"
        label="url"
        :prop="{ placeholder: 'media player url' }"
      ></ab-setting>
    </div>
  </ab-fold-panel>
</template>
