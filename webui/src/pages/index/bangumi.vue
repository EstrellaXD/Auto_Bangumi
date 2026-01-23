<script lang="ts" setup>
definePage({
  name: 'Bangumi List',
});

const { bangumi, editRule } = storeToRefs(useBangumiStore());
const { getAll, updateRule, enableRule, openEditPopup, ruleManage } =
  useBangumiStore();

const { isMobile } = useBreakpointQuery();

onActivated(() => {
  getAll();
});
</script>

<template>
  <div class="page-bangumi">
    <transition-group
      name="bangumi"
      tag="div"
      class="bangumi-grid"
      :class="{ 'bangumi-grid--centered': isMobile }"
    >
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
</template>

<style lang="scss" scoped>
.page-bangumi {
  overflow: auto;
  flex-grow: 1;
}

.bangumi-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;

  &--centered {
    justify-content: center;
  }
}
</style>

<style>
.bangumi-enter-active,
.bangumi-leave-active {
  transition: opacity var(--transition-normal), transform var(--transition-normal);
}
.bangumi-enter-from,
.bangumi-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
