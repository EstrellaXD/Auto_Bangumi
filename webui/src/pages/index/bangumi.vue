<script lang="ts" setup>
import type { BangumiRule } from '#/bangumi';

definePage({
  name: 'Bangumi List',
});

const { bangumi, editRule } = storeToRefs(useBangumiStore());
const { getAll, updateRule, enableRule, openEditPopup, ruleManage } =
  useBangumiStore();

const { isMobile } = useBreakpointQuery();

// Torrent 管理相关状态
const torrentManage = reactive({
  show: false,
  bangumi: null as BangumiRule | null,
});

function openTorrentManage(bangumiItem: BangumiRule) {
  torrentManage.bangumi = bangumiItem;
  torrentManage.show = true;
}

function closeTorrentManage() {
  torrentManage.show = false;
  torrentManage.bangumi = null;
}

onActivated(() => {
  getAll();
});
</script>

<template>
  <div overflow-auto pr-10 mt-12 flex-grow>
    <div>
      <transition-group
        name="bangumi"
        tag="div"
        gap="10"
        pc:gap="20"
        :class="[
          { 'justify-center': isMobile },
          isMobile ? 'grid grid-cols-3' : 'flex flex-wrap',
        ]"
      >
        <ab-bangumi-card
          v-for="i in bangumi"
          :key="i.id"
          :class="[i.deleted && 'grayscale']"
          :bangumi="i"
          type="primary"
          @click="() => openEditPopup(i)"
          @manage-torrents="(bangumi) => openTorrentManage(bangumi)"
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

      <ab-torrent-manage
        v-model:show="torrentManage.show"
        :bangumi="torrentManage.bangumi"
        @close="closeTorrentManage"
      ></ab-torrent-manage>
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
