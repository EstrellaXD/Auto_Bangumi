<script lang="ts" setup>
const {rss} = storeToRefs(useRSSStore());
const {getAll, updateRSS, deleteRSS} = useRSSStore();

onActivated(() => {
  getAll();
});
definePage({
  name: 'RSS',
});


</script>

<template>
  <ab-fold-panel :title="$t('rss.title')">
    <div flex justify-between>
      <div flex space-x-40px>
        <div text-h3>{{ $t('rss.selectbox') }}</div>
        <div class="spacer-1"></div>
        <div text-h3>{{ $t('rss.name') }}</div>
        <div class="spacer-2"></div>
        <div text-h3>{{ $t('rss.url') }}</div>
      </div>
      <div>
        <div text-h3>{{ $t('rss.status') }}</div>
      </div>
    </div>
    <div line my-12px></div>
    <div>
      <ab-rss-item
          v-for="i in rss"
          :key="i.id"
          :name="i.name"
          :url="i.url"
          :enable="i.enabled"
          :parser="i.parser"
          :aggregate="i.aggregate">
      </ab-rss-item>
    </div>
    <div line my-12px></div>
    <div flex="~ justify-end" space-x-10px>
      <ab-button icon="edit">{{ $t('rss.disable') }}</ab-button>
      <ab-button class="type-warn" text="delete">{{ $t('rss.delete') }}</ab-button>
    </div>
  </ab-fold-panel>
</template>

<style lang="scss" scoped>
.spacer-1 {
  width: 32px;
}
.spacer-2 {
  width: 200px;
}

</style>
