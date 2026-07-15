<script lang="ts" setup>
import {
  AddOne,
  Calendar,
  Download,
  Format,
  Home,
  Log,
  Logout,
  Me,
  Moon,
  Pause,
  Play,
  PlayOne,
  Power,
  Refresh,
  Rss,
  SettingTwo,
  Sun,
  Translate,
} from '@icon-park/vue-next';
import { nextTick, ref } from 'vue';
import AbBottomSheet from '@/components/basic/ab-bottom-sheet.vue';
import AbChangeAccount from '@/components/ab-change-account.vue';
import { useAddRss } from '@/hooks/useAddRss';
import { useAppInfo } from '@/hooks/useAppInfo';
import { useAuth } from '@/hooks/useAuth';
import { useConfirm } from '@/hooks/useConfirm';
import { useDarkMode } from '@/hooks/useDarkMode';
import { useMyI18n } from '@/hooks/useMyI18n';
import { useProgramStore } from '@/store/program';

defineProps<{
  show: boolean;
}>();

const emit = defineEmits<{
  (event: 'update:show', value: boolean): void;
}>();

const { t, changeLocale } = useMyI18n();
const { isDark, toggle: toggleDark } = useDarkMode();
const { running, statusKnown } = useAppInfo();
const { openAddRss } = useAddRss();
const { logout } = useAuth();
const { confirm } = useConfirm();
const { start, pause, restart, shutdown, resetRule } = useProgramStore();

const showAccount = ref(false);

const pageItems = [
  { path: '/bangumi', label: 'mobile.bangumi', icon: Home },
  { path: '/calendar', label: 'sidebar.calendar', icon: Calendar },
  { path: '/rss', label: 'sidebar.rss', icon: Rss },
  { path: '/downloader', label: 'sidebar.downloader', icon: Download },
  { path: '/player', label: 'sidebar.player', icon: Play },
  { path: '/log', label: 'sidebar.log', icon: Log },
  { path: '/config', label: 'sidebar.config', icon: SettingTwo },
] as const;

function close() {
  emit('update:show', false);
}

async function openAddRssSheet() {
  close();
  await nextTick();
  openAddRss();
}

async function openAccount() {
  close();
  await nextTick();
  showAccount.value = true;
}

async function toggleProgram() {
  if (!statusKnown.value) return;
  close();
  if (running.value) {
    await pause();
  } else {
    await start();
  }
}

async function confirmAction(
  titleKey: string,
  bodyKey: string,
  action: () => unknown | Promise<unknown>,
  danger = false
) {
  close();
  await nextTick();
  const accepted = await confirm({
    title: t(titleKey),
    body: t(bodyKey),
    danger,
  });
  if (!accepted) return;
  await action();
}
</script>

<template>
  <AbBottomSheet
    :show="show"
    :title="t('common.moreActions')"
    :close-label="t('common.close')"
    @update:show="emit('update:show', $event)"
  >
    <div class="mobile-more">
      <section class="mobile-more__section" aria-labelledby="mobile-more-quick">
        <h3 id="mobile-more-quick" class="mobile-more__heading">
          {{ t('mobile.quick_actions') }}
        </h3>
        <button
          type="button"
          class="mobile-more__action mobile-more__action--primary"
          data-action="add-rss"
          @click="openAddRssSheet"
        >
          <AddOne :size="20" aria-hidden="true" />
          <span>{{ t('topbar.add.title') }}</span>
        </button>
      </section>

      <section class="mobile-more__section" aria-labelledby="mobile-more-pages">
        <h3 id="mobile-more-pages" class="mobile-more__heading">
          {{ t('mobile.pages') }}
        </h3>
        <div class="mobile-more__routes">
          <RouterLink
            v-for="item in pageItems"
            :key="item.path"
            :to="item.path"
            class="mobile-more__route"
            @click="close"
          >
            <span class="mobile-more__icon" aria-hidden="true">
              <Component :is="item.icon" :size="20" />
            </span>
            <span>{{ t(item.label) }}</span>
          </RouterLink>
        </div>
      </section>

      <section
        class="mobile-more__section"
        aria-labelledby="mobile-more-program"
      >
        <h3 id="mobile-more-program" class="mobile-more__heading">
          {{ t('mobile.program') }}
        </h3>
        <button
          type="button"
          class="mobile-more__action"
          data-action="program-toggle"
          :disabled="!statusKnown"
          @click="toggleProgram"
        >
          <Pause v-if="statusKnown && running" :size="20" aria-hidden="true" />
          <PlayOne v-else :size="20" aria-hidden="true" />
          <span>
            {{
              statusKnown
                ? running
                  ? t('topbar.pause')
                  : t('topbar.start')
                : t('mobile.unavailable')
            }}
          </span>
        </button>

        <details class="mobile-more__danger">
          <summary>{{ t('mobile.more_program_actions') }}</summary>
          <div class="mobile-more__danger-actions">
            <button
              type="button"
              data-action="restart"
              @click="
                confirmAction(
                  'mobile.confirm_restart',
                  'mobile.confirm_restart_body',
                  restart
                )
              "
            >
              <Refresh :size="18" aria-hidden="true" />
              {{ t('topbar.restart') }}
            </button>
            <button
              type="button"
              data-action="shutdown"
              @click="
                confirmAction(
                  'mobile.confirm_shutdown',
                  'mobile.confirm_shutdown_body',
                  shutdown,
                  true
                )
              "
            >
              <Power :size="18" aria-hidden="true" />
              {{ t('topbar.shutdown') }}
            </button>
            <button
              type="button"
              data-action="reset-rule"
              @click="
                confirmAction(
                  'mobile.confirm_reset',
                  'mobile.confirm_reset_body',
                  resetRule,
                  true
                )
              "
            >
              <Format :size="18" aria-hidden="true" />
              {{ t('topbar.reset_rule') }}
            </button>
          </div>
        </details>
      </section>

      <section
        class="mobile-more__section"
        aria-labelledby="mobile-more-preferences"
      >
        <h3 id="mobile-more-preferences" class="mobile-more__heading">
          {{ t('mobile.preferences') }}
        </h3>
        <div class="mobile-more__actions-grid">
          <button type="button" data-action="theme" @click="toggleDark">
            <Sun v-if="isDark" :size="20" aria-hidden="true" />
            <Moon v-else :size="20" aria-hidden="true" />
            <span>{{ isDark ? t('theme.light') : t('theme.dark') }}</span>
          </button>
          <button type="button" data-action="locale" @click="changeLocale">
            <Translate :size="20" aria-hidden="true" />
            <span>{{ t('mobile.language') }}</span>
          </button>
          <button type="button" data-action="account" @click="openAccount">
            <Me :size="20" aria-hidden="true" />
            <span>{{ t('topbar.profile.title') }}</span>
          </button>
          <button
            type="button"
            class="mobile-more__logout"
            data-action="logout"
            @click="
              confirmAction(
                'mobile.confirm_logout',
                'mobile.confirm_logout_body',
                logout,
                true
              )
            "
          >
            <Logout :size="20" aria-hidden="true" />
            <span>{{ t('sidebar.logout') }}</span>
          </button>
        </div>
      </section>
    </div>
  </AbBottomSheet>

  <AbChangeAccount v-model:show="showAccount" />
</template>

<style lang="scss" scoped>
.mobile-more,
.mobile-more__section {
  display: flex;
  flex-direction: column;
}

.mobile-more {
  gap: 20px;
}

.mobile-more__section {
  gap: 8px;
}

.mobile-more__heading {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.mobile-more__routes,
.mobile-more__actions-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.mobile-more__route,
.mobile-more__action,
.mobile-more__actions-grid button,
.mobile-more__danger-actions button {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  min-height: var(--touch-target);
  padding: 10px 12px;
  color: var(--color-text);
  background: var(--color-surface-2);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  text-align: left;
  text-decoration: none;
  transition: color var(--transition-fast),
    background-color var(--transition-fast), border-color var(--transition-fast);

  &:hover,
  &:focus-visible {
    color: var(--color-primary);
    background: var(--color-primary-light);
    border-color: var(--color-primary-alpha);
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }
}

.mobile-more__action--primary {
  color: var(--color-primary);
}

.mobile-more__icon {
  display: inline-flex;
  flex: 0 0 auto;
  color: var(--color-primary);
}

.mobile-more__danger {
  color: var(--color-text-secondary);
  font-size: 13px;

  summary {
    display: flex;
    align-items: center;
    min-height: var(--touch-target);
    cursor: pointer;
  }
}

.mobile-more__danger-actions {
  display: grid;
  gap: 8px;

  button {
    color: var(--color-danger);
    background: var(--color-danger-light);
  }
}

.mobile-more__logout {
  color: var(--color-danger) !important;
}
</style>
