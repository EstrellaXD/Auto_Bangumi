<script lang="ts" setup>
import type { BangumiRule } from '#/bangumi';

const { data } = storeToRefs(useBangumiStore());
const { getAll, useUpdateRule, useDisableRule, useEnableRule, useDeleteRule } =
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
const { execute: deleteRule, onResult: onDeleteRuleResult } = useDeleteRule();
const message = useMessage();

onUpdateRuleResult(({ msg }) => {
  message.success(msg);
  refresh();
});

onDisableRuleResult(({ msg }) => {
  message.success(msg);
  refresh();
});

onEnableRuleResult(({ msg }) => {
  message.success(msg);
  refresh();
});

onDeleteRuleResult(({ msg }) => {
  message.success(msg);
  refresh();
});

onActivated(() => {
  getAll();
});

function ruleManage(
  type: 'disable' | 'delete',
  id: number,
  deleteFile: boolean
) {
  if (type === 'disable') {
    disableRule(id, deleteFile);
  }
  if (type === 'delete') {
    deleteRule(id, deleteFile);
  }
}

definePage({
  name: 'Bangumi List',
});
</script>

<template>
  <div overflow-auto mt-12px flex-grow>
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
        @delete-file="
          (type, { id, deleteFile }) => ruleManage(type, id, deleteFile)
        "
        @apply="(rule) => updateRule(rule.id, rule)"
      ></ab-edit-rule>
    </div>
  </div>
</template>
