<script lang="ts" setup>
import type { BangumiRule } from '#/bangumi';

const { data } = storeToRefs(useBangumiStore());
const { getAll, updateRule, removeRule } = useBangumiStore();

const editRule = reactive<{
  show: boolean;
  item: BangumiRule;
}>({
  show: false,
  item: {
    added: false,
    deleted: false,
    dpi: '',
    eps_collect: false,
    filter: [],
    group_name: '',
    id: 0,
    official_title: '',
    offset: 0,
    poster_link: '',
    rss_link: [],
    rule_name: '',
    save_path: '',
    season: 1,
    season_raw: '',
    source: null,
    subtitle: '',
    title_raw: '',
    year: null,
  },
});

async function open(data: BangumiRule) {
  editRule.show = true;
  editRule.item = data;
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

async function applyRule(newData: BangumiRule) {
  const res = await updateRule(newData);
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
      @click="() => open(i)"
    ></ab-bangumi-card>

    <AbEditRule
      v-model:show="editRule.show"
      v-model:rule="editRule.item"
      @delete="deleteRule"
      @apply="applyRule"
    ></AbEditRule>
  </div>
</template>
