<script lang="ts" setup>
const { data } = storeToRefs(useBangumiStore());
const { getAll } = useBangumiStore();

getAll();

definePage({
  name: 'Bangumi List',
});
</script>

<template>
  <div flex="~ wrap" space-y-12px space-x-50px>
    <ab-bangumi-card
      v-for="i in data"
      :key="i.id"
      :poster="i.poster_link"
      :name="i.official_title"
      :season="i.season"
    ></ab-bangumi-card>
  </div>
</template>
