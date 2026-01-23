<script lang="ts" setup>
definePage({
  name: 'Player',
});

const { url } = storeToRefs(usePlayerStore());
</script>

<template>
  <div class="page-embed">
    <template v-if="url === ''">
      <div class="embed-empty">
        <RouterLink to="/config" class="embed-link">
          {{ $t('player.hit') }}
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
