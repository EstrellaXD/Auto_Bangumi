<script lang="ts" setup>
import type { InfoTag } from '@/hooks/useBangumiRuleForm';

defineProps<{
  tags: InfoTag[];
}>();
</script>

<template>
  <div v-if="tags.length > 0" class="info-tags">
    <!-- 剧场版/特别篇用 info 标记与常规元数据区分，其余为中性标签 -->
    <ab-tag
      v-for="tag in tags"
      :key="tag.type"
      :type="tag.type === 'etype' ? 'info' : 'neutral'"
    >
      {{ tag.i18n ? $t(tag.value) : tag.value }}
    </ab-tag>
  </div>
</template>

<style lang="scss" scoped>
.info-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
