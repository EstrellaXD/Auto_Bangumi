<script lang="ts" setup>
const { t } = useMyI18n();
const setupStore = useSetupStore();
const { accountData } = storeToRefs(setupStore);

const isValid = computed(() => {
  return (
    accountData.value.username.length >= 4 &&
    accountData.value.password.length >= 8 &&
    accountData.value.password === accountData.value.confirmPassword
  );
});

const passwordError = computed(() => {
  if (accountData.value.username && accountData.value.username.length < 4) {
    return t('setup.account.username_too_short');
  }
  if (accountData.value.password && accountData.value.password.length < 8) {
    return t('setup.account.password_too_short');
  }
  if (
    accountData.value.confirmPassword &&
    accountData.value.password !== accountData.value.confirmPassword
  ) {
    return t('setup.account.password_mismatch');
  }
  return '';
});
</script>

<template>
  <ab-container :title="t('setup.account.title')" class="wizard-step">
    <div class="step-content">
      <p class="step-subtitle">
        {{ t('setup.account.subtitle') }}
      </p>

      <div class="form-fields">
        <ab-field :label="t('setup.account.username')">
          <ab-input
            v-model="accountData.username"
            :aria-label="t('setup.account.username')"
            autocomplete="username"
            placeholder="admin"
          />
        </ab-field>

        <ab-field :label="t('setup.account.password')">
          <ab-input
            v-model="accountData.password"
            type="password"
            :aria-label="t('setup.account.password')"
            autocomplete="new-password"
          />
        </ab-field>

        <ab-field :label="t('setup.account.confirm_password')">
          <ab-input
            v-model="accountData.confirmPassword"
            type="password"
            :aria-label="t('setup.account.confirm_password')"
            autocomplete="new-password"
          />
        </ab-field>

        <p v-if="passwordError" class="error-text">
          {{ passwordError }}
        </p>
      </div>

      <div class="wizard-actions">
        <ab-button size="sm" variant="secondary" @click="setupStore.prevStep()">
          {{ t('setup.nav.previous') }}
        </ab-button>
        <ab-button
          variant="primary"
          size="sm"
          :disabled="!isValid"
          @click="setupStore.nextStep()"
        >
          {{ t('setup.nav.next') }}
        </ab-button>
      </div>
    </div>
  </ab-container>
</template>

<style lang="scss" scoped>
.wizard-step {
  width: 100%;
}

.step-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.step-subtitle {
  font-size: 12px;
  color: var(--color-text-muted);
  margin: 0;
}

.form-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.error-text {
  font-size: 11px;
  color: var(--color-danger);
  margin: 0;
}

.wizard-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}
</style>
