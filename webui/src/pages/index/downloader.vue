<script lang="ts" setup>
definePage({
  name: 'Downloader',
});

const { config } = storeToRefs(useConfigStore());
const { getConfig } = useConfigStore();

const isNull = computed(() => {
  return config.value.downloader.host === '';
});

const url = computed(() => {
  const downloader = config.value.downloader;
  const host = downloader.host.replace(/http(s?)\:\/\//, '');
  const protocol = downloader.ssl ? 'https' : 'http';

  return `${protocol}://${host}`;
});

onActivated(() => {
  getConfig();
});
</script>

<template>
  <div class="page-embed">
    <template v-if="isNull">
      <div class="embed-empty">
        <RouterLink to="/config" class="embed-link">
          {{ $t('downloader.hit') }}
        </RouterLink>
      </div>
    </template>

    <iframe
      v-else
      :src="url"
      frameborder="0"
      allowfullscreen="true"
      class="embed-frame"
    ></iframe>
  </div>
</template>

<style lang="scss" scoped>
.page-embed {
  overflow: auto;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}

.embed-empty {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.embed-link {
  font-size: 24px;
  color: var(--color-primary);
  text-decoration: none;
  transition: color var(--transition-fast);

  &:hover {
    text-decoration: underline;
    color: var(--color-primary-hover);
  }
}

.embed-frame {
  width: 100%;
  height: 100%;
  flex: 1;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}
</style>
