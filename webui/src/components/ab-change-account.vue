<script lang="ts" setup>
const show = defineModel('show', {
  default: false,
});

const { user, update } = useAuth();
</script>

<template>
  <ab-modal
    v-model:show="show"
    size="sm"
    :title="$t('topbar.profile.pop_title')"
  >
    <div space-y-16>
      <ab-field :label="$t('topbar.profile.username')">
        <ab-input
          v-model="user.username"
          :placeholder="$t('topbar.profile.username')"
        />
      </ab-field>

      <ab-field :label="$t('topbar.profile.password')">
        <ab-input
          v-model="user.password"
          type="password"
          :placeholder="$t('topbar.profile.password')"
        />
      </ab-field>
    </div>

    <template #footer>
      <ab-button variant="primary" size="sm" @click="update">{{
        $t('topbar.profile.update_btn')
      }}</ab-button>
    </template>
  </ab-modal>
</template>
