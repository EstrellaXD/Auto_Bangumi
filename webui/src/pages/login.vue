<script lang="ts" setup>
const { user, login } = useAuth();

definePage({
  name: 'Login',
});
</script>

<template>
  <div f-cer layout-container>
    <ab-container :title="$t('login.title')" w-365px>
      <div space-y-16px>
        <ab-label :label="$t('login.username')">
          <input
            v-model="user.username"
            type="text"
            placeholder="username"
            ab-input
          />
        </ab-label>

        <ab-label :label="$t('login.password')">
          <input
            v-model="user.password"
            type="password"
            placeholder="password"
            ab-input
            @keyup.enter="login"
          />
        </ab-label>

        <div line></div>

        <div flex="~ justify-end">
          <ab-button size="small" @click="login">{{
            $t('login.login_btn')
          }}</ab-button>
        </div>
      </div>
    </ab-container>
  </div>
</template>
