<script lang="ts" setup>
definePage({
  name: 'Downloader',
});

const { config } = storeToRefs(useConfigStore());
const { getConfig } = useConfigStore();

getConfig();

const isNull = computed(() => {
  return config.value.downloader.host === '';
});

const url = computed(() => {
  const downloader = config.value.downloader;
  const protocol = downloader.ssl ? 'https' : 'http';

  return `${protocol}://${downloader.host}`;
});
</script>

<template>
  <div overflow-auto mt-12px flex-grow>
    <template v-if="isNull">
      <div wh-full f-cer text-h1 text-primary>
        <RouterLink to="/config" hover:underline>{{
          $t('downloader.hit')
        }}</RouterLink>
      </div>
    </template>

    <iframe
      :src="url"
      frameborder="0"
      allowfullscreen="true"
      w-full
      h-full
      flex-1
      rounded-12px
    ></iframe>
  </div>
</template>
