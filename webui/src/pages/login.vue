<script lang="ts" setup>
import { Fingerprint, Lock, User } from '@icon-park/vue-next';

definePage({
  name: 'Login',
});

const { user, login } = useAuth();
const { isSupported, loginWithPasskey } = usePasskey();

const isPasskeyLoading = ref(false);
const isLoginLoading = ref(false);

async function handlePasskeyLogin() {
  isPasskeyLoading.value = true;
  try {
    // Pass username if provided, otherwise use discoverable credentials mode
    await loginWithPasskey(user.username || undefined);
  } finally {
    isPasskeyLoading.value = false;
  }
}

async function handleLogin() {
  isLoginLoading.value = true;
  try {
    await login();
  } finally {
    isLoginLoading.value = false;
  }
}
</script>

<template>
  <div class="page-login">
    <!-- Animated background -->
    <div class="login-bg">
      <div class="login-bg-gradient"></div>
      <div class="login-bg-pattern"></div>
    </div>

    <!-- Login card -->
    <div class="login-card">
      <!-- Logo / Brand -->
      <div class="login-header">
        <div class="login-logo">
          <!-- Light mode: colored logo, Dark mode: light logo -->
          <img src="/images/logo.svg" alt="AutoBangumi" class="logo-dark" />
          <img src="/images/logo-light.svg" alt="AutoBangumi" class="logo-light" />
        </div>
        <h1 class="login-title">AutoBangumi</h1>
        <p class="login-subtitle">{{ $t('login.title') }}</p>
      </div>

      <!-- Form -->
      <form class="login-form" @submit.prevent="handleLogin">
        <div class="input-group">
          <label for="login-username" class="input-label">
            {{ $t('login.username') }}
          </label>
          <div class="input-wrapper">
            <User class="input-icon" size="18" />
            <input
              id="login-username"
              v-model="user.username"
              type="text"
              autocomplete="username"
              :placeholder="$t('login.username')"
              class="login-input"
            />
          </div>
        </div>

        <div class="input-group">
          <label for="login-password" class="input-label">
            {{ $t('login.password') }}
          </label>
          <div class="input-wrapper">
            <Lock class="input-icon" size="18" />
            <input
              id="login-password"
              v-model="user.password"
              type="password"
              autocomplete="current-password"
              :placeholder="$t('login.password')"
              class="login-input"
            />
          </div>
        </div>

        <!-- Actions -->
        <div class="login-actions">
          <ab-button
            size="big"
            type="primary"
            :loading="isLoginLoading"
            :disabled="isLoginLoading"
            @click="handleLogin"
          >
            {{ $t('login.login_btn') }}
          </ab-button>

          <button
            v-if="isSupported"
            type="button"
            class="passkey-btn"
            :disabled="isPasskeyLoading"
            @click="handlePasskeyLogin"
          >
            <Fingerprint size="20" />
            <span>{{ $t('login.passkey_btn') }}</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.page-login {
  position: relative;
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

// Animated background
.login-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.login-bg-gradient {
  position: absolute;
  inset: 0;
  background: var(--color-bg);

  &::before,
  &::after {
    content: '';
    position: absolute;
    border-radius: 50%;
    filter: blur(100px);
    opacity: 0.6;
    animation: float 20s ease-in-out infinite;
    will-change: transform;
  }

  &::before {
    width: 600px;
    height: 600px;
    background: var(--color-primary);
    top: -200px;
    right: -100px;
    opacity: 0.15;
  }

  &::after {
    width: 500px;
    height: 500px;
    background: var(--color-accent);
    bottom: -150px;
    left: -100px;
    opacity: 0.1;
    animation-delay: -10s;
  }
}

.login-bg-pattern {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(var(--color-border) 1px, transparent 1px);
  background-size: 32px 32px;
  opacity: 0.5;
}

@keyframes float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  33% {
    transform: translate(30px, -30px) scale(1.05);
  }
  66% {
    transform: translate(-20px, 20px) scale(0.95);
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-bg-gradient::before,
  .login-bg-gradient::after {
    animation: none;
  }
}

// Login card
.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 400px;
  margin: 0 var(--layout-padding);
  padding: 40px 32px;
  background: color-mix(in srgb, var(--color-surface) 80%, transparent);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-lg),
              0 0 0 1px color-mix(in srgb, var(--color-white) 5%, transparent) inset;

  @media (max-width: 480px) {
    padding: 32px 24px;
    margin: 0 16px;
  }
}

// Header
.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  margin-bottom: 16px;

  img {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }

  // Light mode: show colored logo
  .logo-dark {
    display: block;
  }
  .logo-light {
    display: none;
  }
}

// Dark mode: show white logo
:global(.dark) .login-logo {
  .logo-dark {
    display: none;
  }
  .logo-light {
    display: block;
  }
}

.login-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 4px;
  letter-spacing: -0.02em;
}

.login-subtitle {
  font-size: 14px;
  color: var(--color-text-muted);
  margin: 0;
}

// Form
.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  padding-left: 2px;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 14px;
  color: var(--color-text-muted);
  pointer-events: none;
  transition: color var(--transition-fast);
}

.login-input {
  width: 100%;
  height: 44px;
  padding: 0 14px 0 44px;
  font-size: 14px;
  color: var(--color-text);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  outline: none;
  transition: border-color var(--transition-fast),
              box-shadow var(--transition-fast),
              background-color var(--transition-fast);

  &::placeholder {
    color: var(--color-text-muted);
  }

  &:hover {
    border-color: var(--color-border-hover);
  }

  &:focus {
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 15%, transparent);
    background: var(--color-surface);

    ~ .input-icon,
    + .input-icon {
      color: var(--color-primary);
    }
  }

  // When input has value, also highlight icon
  &:not(:placeholder-shown) ~ .input-icon,
  &:not(:placeholder-shown) + .input-icon {
    color: var(--color-text-secondary);
  }
}

// Fix icon color on focus (sibling selector)
.input-wrapper:focus-within .input-icon {
  color: var(--color-primary);
}

// Actions
.login-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 8px;

  // Override ab-button max-width to be full width
  :deep(.btn) {
    max-width: 100%;
  }
}

.passkey-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  height: 44px;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover:not(:disabled) {
    color: var(--color-primary);
    border-color: var(--color-primary);
    border-style: solid;
    background: color-mix(in srgb, var(--color-primary) 5%, transparent);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}
</style>
