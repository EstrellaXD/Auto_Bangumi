<script lang="ts" setup>
definePage({
  name: 'Player',
});

const { url } = storeToRefs(usePlayerStore());
</script>

<template>
  <template v-if="url === ''">
    <div wh-full f-cer text-h1 text-primary>
      <RouterLink to="/config" hover:underline
        >Please set up the media player</RouterLink
      >
    </div>
  </template>

  <iframe
    v-else
    :src="url"
    frameborder="0"
    allowfullscreen="true"
    w-full
    h-full
    flex-1
    rounded-12px
  ></iframe>
</template>
