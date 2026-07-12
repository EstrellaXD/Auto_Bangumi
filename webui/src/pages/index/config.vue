<script lang="ts" setup>
import type { Component } from 'vue';
import { useConfirm } from '@/hooks/useConfirm';
import type { Config } from '#/config';
import ConfigNormal from '@/components/setting/config-normal.vue';
import ConfigParser from '@/components/setting/config-parser.vue';
import ConfigDownload from '@/components/setting/config-download.vue';
import ConfigManage from '@/components/setting/config-manage.vue';
import ConfigNotification from '@/components/setting/config-notification.vue';
import ConfigProxy from '@/components/setting/config-proxy.vue';
import ConfigNetwork from '@/components/setting/config-network.vue';
import ConfigSearchProvider from '@/components/setting/config-search-provider.vue';
import ConfigPlayer from '@/components/setting/config-player.vue';
import ConfigLlm from '@/components/setting/config-llm.vue';
import ConfigPasskey from '@/components/setting/config-passkey.vue';
import ConfigSecurity from '@/components/setting/config-security.vue';
import ConfigAccess from '@/components/setting/config-access.vue';
import UpdateCard from '@/components/setting/update-card.vue';
import { configSectionMatches } from '@/utils/config-search';

definePage({
  name: 'Config',
});

const { t } = useMyI18n();
const { confirm } = useConfirm();
const configStore = useConfigStore();
const { getConfig, setConfig } = configStore;
const { dirtyGroups, isDirty } = storeToRefs(configStore);
const { isMobileOrTablet } = useBreakpointQuery();

async function onDiscardClick() {
  const ok = await confirm({
    title: t('config.discard'),
    body: t('config.discard_confirm'),
    confirmText: t('config.discard'),
    danger: true,
  });
  if (ok) handleDiscard();
}

async function onSaveClick() {
  const ok = await confirm({
    title: t('config.save_restart'),
    body: t('config.restart_confirm'),
    confirmText: t('config.save_restart'),
  });
  if (ok) handleSave();
}

interface ConfigSection {
  id: string;
  titleKey: string;
  component: Component;
  /** 参与全局保存/脏值比对的配置段；空数组 = 该卡片即时自存 */
  groups: Array<keyof Config>;
  keywords: string[];
  /** 当前 locale 下也应参与搜索的可见字段/选项文案。 */
  keywordKeys?: string[];
}

const sections: ConfigSection[] = [
  {
    id: 'normal',
    titleKey: 'config.normal_set.title',
    component: ConfigNormal,
    groups: ['program', 'log'],
    keywords: ['program', 'rss', 'interval', 'port', 'debug', 'log'],
  },
  {
    id: 'parser',
    titleKey: 'config.parser_set.title',
    component: ConfigParser,
    groups: ['rss_parser'],
    keywords: [
      'parser',
      'engine',
      'classic',
      'preview',
      'tokenizer',
      'language',
      'filter',
      'exclude',
    ],
    keywordKeys: [
      'config.parser_set.engine',
      'config.parser_set.engine_classic',
      'config.parser_set.engine_tokenizer',
    ],
  },
  {
    id: 'downloader',
    titleKey: 'config.downloader_set.title',
    component: ConfigDownload,
    groups: ['downloader'],
    keywords: ['qbittorrent', 'host', 'username', 'password', 'ssl', 'path'],
  },
  {
    id: 'manage',
    titleKey: 'config.manage_set.title',
    component: ConfigManage,
    groups: ['bangumi_manage'],
    keywords: [
      'rename',
      'method',
      'eps',
      'group',
      'tag',
      'torrent',
      'revision',
      'conflict',
      'version',
      '修订',
      '冲突',
    ],
    keywordKeys: [
      'config.manage_set.revision_conflict_policy',
      'config.manage_set.revision_conflict_hold',
      'config.manage_set.revision_conflict_replace',
    ],
  },
  {
    id: 'notification',
    titleKey: 'config.notification_set.title',
    component: ConfigNotification,
    groups: ['notification'],
    keywords: [
      'telegram',
      'discord',
      'bark',
      'wecom',
      'gotify',
      'pushover',
      'webhook',
      'token',
    ],
  },
  {
    id: 'proxy',
    titleKey: 'config.proxy_set.title',
    component: ConfigProxy,
    groups: ['proxy'],
    keywords: ['proxy', 'http', 'socks5', 'host', 'port'],
  },
  {
    id: 'network',
    titleKey: 'config.network_set.title',
    component: ConfigNetwork,
    groups: ['network'],
    keywords: ['network', 'tmdb', 'bangumi', 'bgm', 'mirror', 'api', 'key'],
  },
  {
    id: 'search-provider',
    titleKey: 'config.search_provider_set.title',
    component: ConfigSearchProvider,
    groups: [],
    keywords: ['search', 'provider', 'mikan', 'url'],
  },
  {
    id: 'player',
    titleKey: 'config.media_player_set.title',
    component: ConfigPlayer,
    groups: [],
    keywords: ['player', 'plex', 'jellyfin', 'url'],
  },
  {
    id: 'llm',
    titleKey: 'config.llm_set.title',
    component: ConfigLlm,
    groups: ['llm'],
    keywords: ['llm', 'openai', 'anthropic', 'gemini', 'api', 'model'],
  },
  {
    id: 'passkey',
    titleKey: 'passkey.title',
    component: ConfigPasskey,
    groups: [],
    keywords: ['passkey', 'webauthn', 'login'],
  },
  {
    id: 'access',
    titleKey: 'access.title',
    component: ConfigAccess,
    groups: [],
    keywords: ['user', 'account', 'token', 'api', 'mcp', 'access'],
  },
  {
    id: 'security',
    titleKey: 'config.security_set.title',
    component: ConfigSecurity,
    groups: ['security'],
    keywords: ['security', 'whitelist', 'ip', 'token', 'mcp'],
  },
  {
    id: 'update',
    titleKey: 'update.title',
    // 更新卡片自持久化（渠道/自动检查直接写回配置，apply/rollback 独立），
    // 不参与全局保存，故 groups 为空
    component: UpdateCard,
    groups: [],
    keywords: ['update', 'version', 'upgrade', 'release', 'rollback'],
  },
];

// --- 搜索 ---
const searchQuery = ref('');

function sectionMatches(section: ConfigSection): boolean {
  return configSectionMatches(section, searchQuery.value, t);
}

const visibleSections = computed(() => sections.filter(sectionMatches));

// --- 脏值 ---
function sectionDirty(section: ConfigSection): boolean {
  return section.groups.some((g) => dirtyGroups.value.includes(g));
}

const dirtySectionTitles = computed(() =>
  sections.filter(sectionDirty).map((s) => t(s.titleKey))
);

// --- 分区定位 ---
const scrollEl = ref<HTMLElement | null>(null);
const activeSection = ref(sections[0].id);
const sectionEls = new Map<string, HTMLElement>();

function setSectionEl(id: string, el: unknown) {
  if (el instanceof HTMLElement) sectionEls.set(id, el);
  else sectionEls.delete(id);
}

function onScroll() {
  const container = scrollEl.value;
  if (!container) return;
  const anchor = container.scrollTop + 80;
  let current = visibleSections.value[0]?.id ?? sections[0].id;
  for (const section of visibleSections.value) {
    const el = sectionEls.get(section.id);
    if (el && el.offsetTop <= anchor) current = section.id;
  }
  activeSection.value = current;
}

function jumpTo(id: string) {
  const el = sectionEls.get(id);
  if (!el) return;
  const reduceMotion = window.matchMedia(
    '(prefers-reduced-motion: reduce)'
  ).matches;
  el.scrollIntoView({
    behavior: reduceMotion ? 'auto' : 'smooth',
    block: 'start',
  });
  activeSection.value = id;
}

// --- 保存 / 放弃 ---
const isSaving = ref(false);
const isResetting = ref(false);
const saveFailed = ref(false);

async function handleSave() {
  isSaving.value = true;
  try {
    const result = await setConfig();
    saveFailed.value = !result.ok;
  } finally {
    isSaving.value = false;
  }
}

async function handleDiscard() {
  isResetting.value = true;
  try {
    await getConfig();
    saveFailed.value = false;
  } finally {
    isResetting.value = false;
  }
}

onActivated(() => {
  // 有未保存修改时不重新拉取，避免静默覆盖用户输入
  if (!isDirty.value) {
    getConfig();
  }
});

onBeforeRouteLeave(() => {
  if (!isDirty.value) return true;
  return confirm({
    title: t('config.leave_confirm'),
    confirmText: t('config.discard'),
    danger: true,
  });
});
</script>

<template>
  <div class="page-config">
    <div class="config-layout">
      <nav
        v-if="!isMobileOrTablet"
        class="config-rail"
        :aria-label="$t('config.search_placeholder')"
      >
        <ab-input
          v-model="searchQuery"
          class="rail-search"
          type="search"
          :placeholder="$t('config.search_placeholder')"
          :aria-label="$t('config.search_placeholder')"
        />
        <button
          v-for="s in visibleSections"
          :key="s.id"
          class="rail-link"
          :class="{ active: activeSection === s.id }"
          :aria-current="activeSection === s.id ? 'true' : undefined"
          @click="jumpTo(s.id)"
        >
          <span class="rail-link-title">{{ $t(s.titleKey) }}</span>
          <span
            v-if="sectionDirty(s)"
            class="dirty-dot"
            :title="$t('config.unsaved_count', 1)"
          ></span>
        </button>
      </nav>

      <div ref="scrollEl" class="config-scroll" @scroll.passive="onScroll">
        <div v-if="visibleSections.length === 0" class="config-no-match">
          <p>{{ $t('config.no_match') }}</p>
          <ab-button size="sm" @click="searchQuery = ''">
            {{ $t('log.clear_filters') }}
          </ab-button>
        </div>

        <div
          v-for="s in visibleSections"
          :key="s.id"
          :ref="(el) => setSectionEl(s.id, el)"
          class="config-section"
          :class="{ 'section-dirty': sectionDirty(s) }"
        >
          <component :is="s.component" />
        </div>
      </div>
    </div>

    <div class="config-actions">
      <span class="unsaved-hint" role="status">
        <template v-if="isDirty">
          <span class="dirty-dot" aria-hidden="true"></span>
          <b>{{ $t('config.unsaved_count', dirtyGroups.length) }}</b>
          <span v-if="!isMobileOrTablet" class="unsaved-sections">
            · {{ dirtySectionTitles.join(', ') }}
          </span>
        </template>
        <template v-else>{{ $t('config.unsaved_none') }}</template>
      </span>

      <ab-button
        :loading="isResetting"
        :disabled="!isDirty || isResetting || isSaving"
        @click="onDiscardClick"
      >
        {{ $t('config.discard') }}
      </ab-button>

      <ab-button
        :variant="saveFailed ? 'danger' : 'primary'"
        :loading="isSaving"
        :disabled="!isDirty || isResetting || isSaving"
        @click="onSaveClick"
      >
        {{ $t('config.save_restart') }}
      </ab-button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.page-config {
  flex-grow: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.config-layout {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 16px;
}

.config-rail {
  width: 190px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
  padding-right: 2px;
}

.rail-search {
  margin-bottom: 8px;
  width: 100%;
}

.rail-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 10px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition: background-color var(--transition-fast),
    color var(--transition-fast);

  &:hover {
    background: var(--color-surface-hover);
    color: var(--color-text);
  }

  &.active {
    background: var(--color-primary-light);
    color: var(--color-primary);
    font-weight: 600;
  }
}

.rail-link-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dirty-dot {
  width: 7px;
  height: 7px;
  border-radius: var(--radius-full);
  background: var(--color-accent);
  flex-shrink: 0;
}

.config-scroll {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: 12px;
  // 让 scrollIntoView 停在分区上缘略下，避免贴边
  scroll-padding-top: 4px;

  @include forDesktop {
    max-width: 860px;
  }
}

.config-section {
  scroll-margin-top: 4px;
}

.config-no-match {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 32px 16px;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.config-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-surface);

  @include forTablet {
    justify-content: flex-end;
  }
}

.unsaved-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  margin-right: auto;
  font-size: 13px;
  color: var(--color-text-secondary);

  b {
    color: var(--color-text);
    font-weight: 600;
    white-space: nowrap;
  }
}

.unsaved-sections {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 639px) {
  .config-actions {
    flex-wrap: wrap;

    .unsaved-hint {
      width: 100%;
    }

    :deep(.ab-btn) {
      flex: 1;
    }
  }
}
</style>
