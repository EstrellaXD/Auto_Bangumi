<script lang="ts" setup>
definePage({
  name: 'RSS',
});

const { rss, selectedRSS } = storeToRefs(useRSSStore());
const { getAll, deleteSelected, disableSelected, enableSelected } =
  useRSSStore();

onActivated(() => {
  getAll();
});

function addSelected(checked: boolean, id: number) {
  if (!checked) {
    selectedRSS.value.push(id);
  } else {
    selectedRSS.value = selectedRSS.value.filter((i) => i !== id);
  }
}
</script>

<template>
  <div overflow-auto mt-12 flex-grow>
    <ab-container :title="$t('rss.title')">
      <div flex="~ justify-between">
        <div flex="~ gap-x-40">
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
      <div line my-12></div>
      <div space-y-12>
        <ab-rss-item
          v-for="i in rss"
          :id="i.id"
          :key="i.id"
          :name="i.name"
          :url="i.url"
          :enable="i.enabled"
          :parser="i.parser"
          :aggregate="i.aggregate"
          @on-select="addSelected"
        >
        </ab-rss-item>
      </div>
      <div v-if="selectedRSS.length > 0">
        <div line my-12></div>
        <div flex="~ justify-end gap-x-10">
          <ab-button @click="enableSelected">{{ $t('rss.enable') }}</ab-button>
          <ab-button @click="disableSelected">{{
            $t('rss.disable')
          }}</ab-button>
          <ab-button class="type-warn" @click="deleteSelected">{{
            $t('rss.delete')
          }}</ab-button>
        </div>
      </div>
    </ab-container>
  </div>
</template>

<style lang="scss" scoped>
.spacer-1 {
  width: 32px;
}

.spacer-2 {
  width: 200px;
}
</style>
