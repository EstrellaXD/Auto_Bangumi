<script lang="ts" setup>
const show = defineModel('show', {
  default: false,
});

const { user, update } = useAuth();
</script>

<template>
  <ab-popup v-model:show="show" title="Change Account" css="w-365px">
    <div space-y-16px>
      <ab-label label="Username">
        <input
          v-model="user.username"
          type="text"
          placeholder="username"
          ab-input
        />
      </ab-label>

      <ab-label label="Password">
        <input
          v-model="user.password"
          type="password"
          placeholder="password"
          ab-input
        />
      </ab-label>

      <div line></div>

      <div flex="~ justify-end">
        <ab-button size="small" @click="update">Update</ab-button>
      </div>
    </div>
  </ab-popup>
</template>
