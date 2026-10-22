<script lang="ts" setup>
import type { BangumiRule } from '#/bangumi';
import { slotTitle, usePluginUi } from '@/hooks/usePluginUi';

definePage({
  name: 'Index',
  redirect: '/bangumi',
});

const { editRule } = storeToRefs(useBangumiStore());
const editRuleOpen = computed({
  get: () => editRule.value.show,
  set: (val) => (editRule.value.show = val),
});
const { comp: EditRule, shown: editRuleShown } = useLazyModal(
  editRuleOpen,
  () => import('@/components/ab-edit-rule.vue')
);

// 插件页面的标题取自清单（清单到达前留空，避免闪出路由名 Plugin；清单已到达
// 或加载失败仍无匹配页面时回退为插件 id）；其它页面用与侧栏相同的翻译，未登记的路由回退为路由名
const route = useRoute();
const { t, lang } = useMyI18n();
const { slots, loaded, loadFailed } = usePluginUi();
const titleKeys: Record<string, string> = {
  Market: 'market.title',
  'Bangumi List': 'sidebar.homepage',
  'Bangumi Torrents': 'homepage.torrents.title',
  'Orphan Torrents': 'homepage.others.title',
  Calendar: 'sidebar.calendar',
  RSS: 'sidebar.rss',
  Player: 'sidebar.player',
  Downloader: 'sidebar.downloader',
  Log: 'sidebar.log',
  Config: 'sidebar.config',
};
const pageTitle = computed(() => {
  const name = String(route.name ?? '');
  if (titleKeys[name]) return t(titleKeys[name]);
  if (route.name !== 'Plugin') return name;
  const id = route.params.id;
  const ui = slots.value.find((s) => s.slot === 'page' && s.plugin_id === id);
  if (ui) return slotTitle(ui, lang.value === 'zh-CN' ? 'zh-CN' : 'en-US');
  return loaded.value || loadFailed.value ? id : '';
});
const { updateRule, enableRule, archiveRule, unarchiveRule, ruleManage } =
  useBangumiStore();

function onEnableRule(id: number) {
  enableRule(id);
}

function onArchiveRule(id: number) {
  archiveRule(id);
}

function onUnarchiveRule(id: number) {
  unarchiveRule(id);
}

function onDeleteFile(
  type: 'disable' | 'delete',
  { id, deleteFile }: { id: number; deleteFile: boolean }
) {
  ruleManage(type, id, deleteFile);
}

function onApplyRule(rule: BangumiRule) {
  updateRule(rule.id, rule);
}
</script>

<template>
  <div class="layout-container">
    <a href="#main-content" class="skip-link">Skip to content</a>

    <ab-topbar />

    <main class="layout-main">
      <ab-sidebar />

      <div id="main-content" class="layout-content">
        <!-- 标题与内容用同一个 page 过渡，切换路由时一起淡出淡入 -->
        <transition name="page" mode="out-in">
          <ab-page-title :key="pageTitle" :title="pageTitle" />
        </transition>

        <RouterView v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <!-- max bounds background re-renders: SSE-fed pages (log,
                 downloader) keep updating while cached -->
            <KeepAlive :max="3">
              <component :is="Component" />
            </KeepAlive>
          </transition>
        </RouterView>
      </div>
    </main>

    <component
      :is="EditRule"
      v-if="EditRule"
      v-model:rule="editRule.item"
      :show="editRuleShown"
      @update:show="editRuleOpen = $event"
      @enable="onEnableRule"
      @archive="onArchiveRule"
      @unarchive="onUnarchiveRule"
      @delete-file="onDeleteFile"
      @apply="onApplyRule"
    />
  </div>
</template>

<style lang="scss" scoped>
.layout-container {
  width: 100%;
  height: 100dvh;
  overflow: hidden;

  padding: var(--layout-padding);
  padding-left: calc(var(--layout-padding) + env(safe-area-inset-left, 0px));
  padding-right: calc(var(--layout-padding) + env(safe-area-inset-right, 0px));
  gap: var(--layout-gap);

  display: flex;
  flex-direction: column;

  background: var(--color-bg);
  transition: background-color var(--transition-normal);

  @include forDesktop {
    min-width: 1024px;
    min-height: 768px;
  }
}

.layout-main {
  display: flex;
  flex-direction: column;
  gap: var(--layout-gap);
  overflow: hidden;
  flex: 1;
  min-height: 0;
  // Clear the fixed bottom nav (only rendered <640px)
  padding-bottom: calc(var(--nav-height) + var(--layout-gap));

  @include forTablet {
    flex-direction: row;
    padding-bottom: 0;
  }

  @include forDesktop {
    flex-direction: row;
  }
}

.layout-content {
  overflow: hidden;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  gap: var(--layout-gap);
}

.skip-link {
  position: absolute;
  top: -100%;
  left: 16px;
  z-index: 100;
  padding: 8px 16px;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-sm);
  font-size: 14px;
  text-decoration: none;
  transition: top var(--transition-fast);

  &:focus {
    top: 16px;
  }
}
</style>
