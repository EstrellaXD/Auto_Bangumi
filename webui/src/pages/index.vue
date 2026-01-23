<script lang="ts" setup>
definePage({
  name: 'Index',
  redirect: '/bangumi',
});

const { editRule } = storeToRefs(useBangumiStore());
const { updateRule, enableRule, ruleManage } = useBangumiStore();
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
      @delete-file="(type, { id, deleteFile }) => ruleManage(type, id, deleteFile)"
      @apply="(rule) => updateRule(rule.id, rule)"
    />
  </div>
</template>

<style lang="scss" scoped>
.layout-container {
  width: 100%;
  height: 100%;

  padding: var(--layout-padding);
  gap: var(--layout-gap);

  display: flex;
  flex-direction: column;

  background: var(--color-bg);
  transition: background-color var(--transition-normal);

  @include forPC {
    min-width: 1024px;
    min-height: 768px;
  }

  @include forMobile {
    overflow: hidden;
    height: 100vh;
  }
}

.layout-main {
  display: flex;
  gap: var(--layout-gap);

  overflow: hidden;
  height: calc(100vh - 2 * var(--layout-padding) - 56px - var(--layout-gap));

  @include forMobile {
    flex-direction: column-reverse;
    height: calc(100vh - var(--layout-padding) * 2 - var(--layout-gap));
    gap: var(--layout-gap);
  }
}

.layout-content {
  overflow: hidden;
  height: 100%;
  display: flex;
  flex-direction: column;
  flex: 1;
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
