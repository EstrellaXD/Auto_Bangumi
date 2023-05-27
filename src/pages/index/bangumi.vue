<script lang="ts" setup>
import type { BangumiRule } from '#/bangumi';
import { AbEditRule } from '#/components';

const { data } = storeToRefs(useBangumiStore());
const { getAll, updateRule, removeRule } = useBangumiStore();

const editRule = reactive<{
  show: boolean;
  item: AbEditRule;
}>({
  show: false,
  item: {
    id: -1,
    official_title: '',
    year: '',
    season: 1,
    offset: 0,
    filter: [],
  },
});

function open(data: BangumiRule) {
  editRule.show = true;
  editRule.item = {
    id: data.id,
    official_title: data.official_title,
    year: data.year ?? '',
    season: data.season,
    offset: data.offset,
    filter: data.filter,
  };
}

async function deleteRule({
  id,
  deleteFile,
}: {
  id: number;
  deleteFile: boolean;
}) {
  const res = await removeRule(id, deleteFile);
  if (res) {
    editRule.show = false;
    getAll();
  }
}

async function applyRule(newData: AbEditRule) {
  const id = newData.id;
  const oldData = await apiBangumi.getRule(id);
  const data = Object.assign(oldData, newData);
  const res = await updateRule(data);
  if (res) {
    editRule.show = false;
    getAll();
  }
}

onActivated(() => {
  getAll();
});

definePage({
  name: 'Bangumi List',
});
</script>

<template>
  <div flex="~ wrap" gap-y-12px gap-x-50px>
    <ab-bangumi-card
      v-for="i in data"
      v-show="!i.deleted"
      :key="i.id"
      :poster="i.poster_link ?? ''"
      :name="i.official_title"
      :season="i.season"
      @click="open(i)"
    ></ab-bangumi-card>

    <AbEditRule
      v-model:show="editRule.show"
      :item="editRule.item"
      @delete="deleteRule"
      @apply="applyRule"
    ></AbEditRule>
  </div>
</template>
