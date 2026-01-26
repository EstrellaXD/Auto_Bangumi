<script lang="ts" setup>
definePage({
  name: 'Index',
  redirect: '/bangumi',
});

const { editRule } = storeToRefs(useBangumiStore());
const { updateRule, enableRule, archiveRule, unarchiveRule, ruleManage } = useBangumiStore();
</script>

<template>
  <div class="layout-container">
    <a href="#main-content" class="skip-link">Skip to content</a>

    <ab-topbar />

    <main class="layout-main">
      <ab-sidebar />

      <div id="main-content" class="layout-content">
        <ab-page-title :title="$route.name"></ab-page-title>

        <RouterView v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <KeepAlive>
              <component :is="Component" />
            </KeepAlive>
          </transition>
        </RouterView>
      </div>
    </main>

    <ab-edit-rule
      v-model:show="editRule.show"
      v-model:rule="editRule.item"
      @enable="(id) => enableRule(id)"
      @archive="(id) => archiveRule(id)"
      @unarchive="(id) => unarchiveRule(id)"
      @delete-file="(type, { id, deleteFile }) => ruleManage(type, id, deleteFile)"
      @apply="(rule) => updateRule(rule.id, rule)"
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

  @include forTablet {
    flex-direction: row;
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
