<script lang="ts" setup>
const show = defineModel('show', {
  default: false,
});

const { user, update } = useAuth();
</script>

<template>
  <ab-popup
    v-model:show="show"
    :title="$t('topbar.profile.poptitle')"
    css="w-365px"
  >
    <div space-y-16px>
      <ab-label :label="$t('topbar.profile.username')">
        <input
          v-model="user.username"
          type="text"
          :placeholder="$t('topbar.profile.username')"
          ab-input
        />
      </ab-label>

      <ab-label :label="$t('topbar.profile.password')">
        <input
          v-model="user.password"
          type="password"
          :placeholder="$t('topbar.profile.password')"
          ab-input
        />
      </ab-label>

      <div line></div>

      <div flex="~ justify-end">
        <ab-button size="small" @click="update">{{
          $t('topbar.profile.updatebtn')
        }}</ab-button>
      </div>
    </div>
  </ab-popup>
</template>
