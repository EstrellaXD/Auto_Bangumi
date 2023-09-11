<script lang="ts" setup>

definePage({
  name: 'Index',
  redirect: '/bangumi',
});

// isMobile is a computed property
const mobile = isMobile();

</script>

<template>
  <div v-if="!mobile" layout-container>
    <ab-topbar/>
    <main layout-main>
      <ab-sidebar/>

      <div layout-content>
        <ab-page-title :title="$route.name"></ab-page-title>

        <RouterView v-slot="{ Component }">
          <KeepAlive>
            <component :is="Component"/>
          </KeepAlive>
        </RouterView>
      </div>
    </main>
  </div>
  <div v-else wh-screen bg-page>
<!--    <RouterView v-slot="{ Component }">-->
<!--      <KeepAlive>-->
<!--        <component :is="Component"/>-->
<!--      </KeepAlive>-->
<!--    </RouterView>-->
    <div flex-col justify-between>
      <ab-topbar :mobile="true"/>
      <ab-bottombar/>
    </div>
  </div>
</template>
