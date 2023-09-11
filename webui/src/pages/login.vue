<script lang="ts" setup>
const {user, login} = useAuth();

definePage({
  name: 'Login',
});

const mobile = isMobile();

</script>

<template>
  <div v-if="!mobile" f-cer layout-container>
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
            }}
          </ab-button>
        </div>
      </div>
    </ab-container>
  </div>
  <div v-else layout-container-mobile>
    <ab-container :title="$t('login.title')" w-300px>
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

        <div f-cer>
          <ab-button size="normal" @click="login">{{
              $t('login.login_btn')
            }}
          </ab-button>
        </div>
      </div>
    </ab-container>
  </div>
</template>
