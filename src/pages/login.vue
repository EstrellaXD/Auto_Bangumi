<script lang="ts" setup>
const { user, login } = useAuth();

definePage({
  name: 'Login',
});
</script>

<template>
  <div f-cer layout-container>
    <ab-container title="Login" w-365px>
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
            type="text"
            placeholder="password"
            ab-input
          />
        </ab-label>

        <div line></div>

        <div flex="~ justify-end">
          <ab-button size="small" @click="login">Login</ab-button>
        </div>
      </div>
    </ab-container>
  </div>
</template>
