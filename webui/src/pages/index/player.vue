<script lang="ts" setup>
definePage({
  name: 'Player',
});

const { url } = storeToRefs(usePlayerStore());
</script>

<template>
  <div class="page-embed">
    <div v-if="url === ''" class="page-empty">
      <ab-empty
        :title="$t('player.empty.title')"
        :description="$t('player.empty.subtitle')"
      >
        <template #action>
          <ol class="empty-steps">
            <li v-for="n in 3" :key="n">
              <span class="empty-steps-title">{{
                $t(`player.empty.step${n}_title`)
              }}</span>
              {{ $t(`player.empty.step${n}_desc`) }}
            </li>
          </ol>
          <ab-button variant="primary" @click="$router.push('/config')">
            {{ $t('sidebar.config') }}
          </ab-button>
        </template>
      </ab-empty>
    </div>

    <iframe
      v-else
      :src="url"
      :title="$t('sidebar.player')"
      frameborder="0"
      allowfullscreen="true"
      class="embed-frame"
    />
  </div>
</template>

<style lang="scss" scoped>
.page-embed {
  overflow: auto;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}

.embed-frame {
  width: 100%;
  height: 100%;
  flex: 1;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}
</style>
