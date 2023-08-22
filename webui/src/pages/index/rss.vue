<script lang="ts" setup>
const { rss } = storeToRefs(useRSSStore());
const { getAll, updateRSS, deleteRSS } = useRSSStore();

onActivated(() => {
  getAll();
});
definePage({
  name: 'RSS',
});
</script>

<template>
  <div>
    <ab-rss-item
        v-for="i in rss"
        :key="i.id"
        :name="i.name"
        :url="i.url"
        :enable="i.enable"
        :parser="i.parser"
        :aggregate="i.aggregate">
    </ab-rss-item>
  </div>
  <div>
    <ab-button-group flex>
      <ab-button icon="edit">{{ $t('config.apply') }}</ab-button>
      <ab-button class="type-warn" text="delete">{{ $t('config.apply') }}</ab-button>
    </ab-button-group>
  </div>
</template>
