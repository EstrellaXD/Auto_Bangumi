<script lang="ts" setup>
const {bangumi, editRule} = storeToRefs(useBangumiStore());
const {getAll, updateRule, enableRule, openEditPopup, ruleManage} =
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
    <div>
      <transition-group
          name="bangumi" tag="div"
          flex="~ wrap" gap-y-12px gap-x-32px>
        <!--      TODO: Transition Effect to fix.   -->
        <ab-bangumi-card
            v-for="i in bangumi"
            :key="i.id"
            :class="[i.deleted && 'grayscale']"
            :bangumi="i"
            type="primary"
            @click="() => openEditPopup(i)"
        ></ab-bangumi-card>
      </transition-group>

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

<style>
.bangumi-enter-active,
.bangumi-leave-active {
  transition: all 0.5s ease;
}
.bangumi-enter-from,
.bangumi-leave-to {
  opacity: 0;
}
</style>
