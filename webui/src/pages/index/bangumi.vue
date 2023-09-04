<script lang="ts" setup>
const { bangumi, editRule } = storeToRefs(useBangumiStore());
const { getAll, updateRule, enableRule, openEditPopup, ruleManage } =
  useBangumiStore();

onActivated(() => {
  getAll();
});

definePage({
  name: 'Bangumi List',
});
</script>

<template>
  <div overflow-auto mt-12px flex-grow>
    <div flex="~ wrap" gap-y-12px gap-x-32px>
      <ab-bangumi-card
        v-for="i in bangumi"
        :key="i.id"
        :class="[i.deleted && 'grayscale']"
        :poster="i.poster_link ?? ''"
        :name="i.official_title"
        :season="i.season"
        @click="() => openEditPopup(i)"
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
