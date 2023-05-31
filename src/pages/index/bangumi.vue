<script lang="ts" setup>
import type { BangumiRule } from '#/bangumi';

const { data } = storeToRefs(useBangumiStore());
const { getAll, useUpdateRule, useDisableRule, useEnableRule } =
  useBangumiStore();

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

function open(data: BangumiRule) {
  editRule.show = true;
  editRule.item = data;
}

function refresh() {
  editRule.show = false;
  getAll();
}

const { execute: updateRule, onResult: onUpdateRuleResult } = useUpdateRule();
const { execute: enableRule, onResult: onEnableRuleResult } = useEnableRule();
const { execute: disableRule, onResult: onDisableRuleResult } =
  useDisableRule();

onUpdateRuleResult(() => {
  refresh();
});

onDisableRuleResult(() => {
  refresh();
});

onEnableRuleResult(() => {
  refresh();
});

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
      :key="i.id"
      :class="[i.deleted && 'grayscale']"
      :poster="i.poster_link ?? ''"
      :name="i.official_title"
      :season="i.season"
      @click="() => open(i)"
    ></ab-bangumi-card>

    <ab-edit-rule
      v-model:show="editRule.show"
      v-model:rule="editRule.item"
      @enable="(id) => enableRule(id)"
      @disable="({ id, deleteFile }) => disableRule(id, deleteFile)"
      @apply="(rule) => updateRule(rule)"
    ></ab-edit-rule>
  </div>
</template>
