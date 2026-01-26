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
      <p class="step-subtitle">{{ t('setup.account.subtitle') }}</p>

      <div class="form-fields">
        <ab-label :label="t('setup.account.username')">
          <input
            v-model="accountData.username"
            type="text"
            placeholder="admin"
            class="setup-input"
          />
        </ab-label>

        <ab-label :label="t('setup.account.password')">
          <input
            v-model="accountData.password"
            type="password"
            class="setup-input"
          />
        </ab-label>

        <ab-label :label="t('setup.account.confirm_password')">
          <input
            v-model="accountData.confirmPassword"
            type="password"
            class="setup-input"
          />
        </ab-label>

        <p v-if="passwordError" class="error-text">{{ passwordError }}</p>
      </div>

      <div class="wizard-actions">
        <ab-button size="small" type="secondary" @click="setupStore.prevStep()">
          {{ t('setup.nav.previous') }}
        </ab-button>
        <ab-button size="small" :disabled="!isValid" @click="setupStore.nextStep()">
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

.setup-input {
  outline: none;
  min-width: 0;
  width: 200px;
  height: 28px;
  padding: 0 12px;
  font-size: 12px;
  text-align: right;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
  }

  &:focus {
    border-color: var(--color-primary);
    box-shadow: 0 0 0 2px rgba(108, 74, 182, 0.2);
  }
}

.error-text {
  font-size: 11px;
  color: var(--color-error, #e53935);
  margin: 0;
}

.wizard-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}
</style>
