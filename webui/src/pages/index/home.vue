<script lang="ts" setup>
import { Download, Home, Refresh, Rss } from '@icon-park/vue-next';
import { computed, onActivated, ref } from 'vue';
import { useAppInfo } from '@/hooks/useAppInfo';
import { useMyI18n } from '@/hooks/useMyI18n';
import { useBangumiStore } from '@/store/bangumi';
import { useDownloaderStore } from '@/store/downloader';
import { useRSSStore } from '@/store/rss';
import {
  summarizeBangumi,
  summarizeDownloads,
  summarizeRss,
} from '@/utils/mobile-overview';

definePage({
  name: 'Home',
});

const { t } = useMyI18n();
const { running, version, statusKnown } = useAppInfo();
const bangumiStore = useBangumiStore();
const rssStore = useRSSStore();
const downloaderStore = useDownloaderStore();

const refreshing = ref(false);

const bangumiSummary = computed(() => summarizeBangumi(bangumiStore.bangumi));
const rssSummary = computed(() => summarizeRss(rssStore.rss));
const downloadSummary = computed(() =>
  summarizeDownloads(downloaderStore.torrents)
);
const activeRules = computed(() =>
  bangumiStore.bangumi
    .filter((rule) => !rule.deleted && !rule.archived)
    .slice(0, 3)
);

const bangumiUnavailable = computed(
  () => bangumiStore.loadFailed && !bangumiStore.hasLoaded
);
const rssUnavailable = computed(
  () => rssStore.loadFailed && !rssStore.hasLoaded
);
const downloadsUnavailable = computed(
  () => downloaderStore.loadFailed && !downloaderStore.hasLoaded
);
const bangumiPending = computed(
  () => !bangumiStore.hasLoaded && !bangumiStore.loadFailed
);
const rssPending = computed(() => !rssStore.hasLoaded && !rssStore.loadFailed);
const downloadsPending = computed(
  () => !downloaderStore.hasLoaded && !downloaderStore.loadFailed
);

function formatSpeed(bytesPerSecond: number) {
  if (bytesPerSecond <= 0) return '0 B/s';
  const units = ['B/s', 'KiB/s', 'MiB/s', 'GiB/s'];
  const index = Math.min(
    Math.floor(Math.log(bytesPerSecond) / Math.log(1024)),
    units.length - 1
  );
  return `${(bytesPerSecond / 1024 ** index).toFixed(1)} ${units[index]}`;
}

async function refresh() {
  if (refreshing.value) return;
  refreshing.value = true;
  try {
    await Promise.all([
      bangumiStore.getAll(),
      rssStore.getAll(),
      downloaderStore.getAll(),
    ]);
  } finally {
    refreshing.value = false;
  }
}

onActivated(refresh);
</script>

<template>
  <div class="page-home">
    <header class="page-home__header">
      <div class="page-home__heading">
        <h1>{{ t('mobile.overview') }}</h1>
        <p>{{ t('mobile.overview_subtitle') }}</p>
      </div>
      <button
        type="button"
        class="page-home__refresh"
        data-action="refresh"
        :aria-label="t('mobile.refresh_overview')"
        :disabled="refreshing"
        @click="refresh"
      >
        <Refresh :size="20" :class="{ 'is-spinning': refreshing }" />
      </button>
    </header>

    <section class="page-home__status" aria-labelledby="home-status-title">
      <div>
        <span id="home-status-title" class="page-home__eyebrow">
          {{ t('mobile.system_status') }}
        </span>
        <ab-status
          :state="statusKnown ? (running ? 'running' : 'stopped') : 'paused'"
          :label="
            statusKnown
              ? running
                ? t('mobile.running')
                : t('mobile.stopped')
              : t('mobile.unavailable')
          "
        />
      </div>
      <span v-if="version" class="page-home__version">v{{ version }}</span>
    </section>

    <section class="page-home__summaries" :aria-label="t('mobile.overview')">
      <RouterLink
        to="/bangumi"
        class="page-home__summary"
        data-summary="bangumi"
      >
        <span class="page-home__summary-icon" aria-hidden="true">
          <Home :size="20" />
        </span>
        <span class="page-home__summary-copy">
          <strong>{{ t('mobile.bangumi') }}</strong>
          <template v-if="bangumiUnavailable">
            <small>{{ t('mobile.unavailable') }}</small>
          </template>
          <template v-else-if="bangumiPending">
            <small>{{ t('common.loading') }}</small>
          </template>
          <template v-else>
            <span data-value="primary">{{ bangumiSummary.active }}</span>
            <small data-value="secondary">
              {{ bangumiSummary.needsReview }}
              {{ t('mobile.needs_review') }}
            </small>
          </template>
        </span>
      </RouterLink>

      <RouterLink to="/rss" class="page-home__summary" data-summary="rss">
        <span class="page-home__summary-icon" aria-hidden="true">
          <Rss :size="20" />
        </span>
        <span class="page-home__summary-copy">
          <strong>{{ t('sidebar.rss') }}</strong>
          <template v-if="rssUnavailable">
            <small>{{ t('mobile.unavailable') }}</small>
          </template>
          <template v-else-if="rssPending">
            <small>{{ t('common.loading') }}</small>
          </template>
          <template v-else>
            <span data-value="primary">{{ rssSummary.enabled }}</span>
            <small data-value="secondary">
              {{ rssSummary.errors }} {{ t('mobile.connection_errors') }}
            </small>
          </template>
        </span>
      </RouterLink>

      <RouterLink
        to="/downloader"
        class="page-home__summary"
        data-summary="downloads"
      >
        <span class="page-home__summary-icon" aria-hidden="true">
          <Download :size="20" />
        </span>
        <span class="page-home__summary-copy">
          <strong>{{ t('sidebar.downloader') }}</strong>
          <template v-if="downloadsUnavailable">
            <small>{{ t('mobile.unavailable') }}</small>
          </template>
          <template v-else-if="downloadsPending">
            <small>{{ t('common.loading') }}</small>
          </template>
          <template v-else>
            <span data-value="primary">{{ downloadSummary.active }}</span>
            <small data-value="secondary">
              {{ formatSpeed(downloadSummary.bytesPerSecond) }}
            </small>
          </template>
        </span>
      </RouterLink>
    </section>

    <RouterLink
      v-if="!bangumiUnavailable && bangumiSummary.needsReview > 0"
      to="/bangumi"
      class="page-home__attention"
    >
      <strong>{{ t('mobile.attention') }}</strong>
      <span>{{ t('mobile.review_attention') }}</span>
    </RouterLink>

    <section class="page-home__active" aria-labelledby="home-active-title">
      <div class="page-home__section-heading">
        <h2 id="home-active-title">{{ t('mobile.active_anime') }}</h2>
        <RouterLink to="/bangumi">{{ t('mobile.view_all') }}</RouterLink>
      </div>
      <div v-if="activeRules.length" class="page-home__rule-list">
        <RouterLink
          v-for="rule in activeRules"
          :key="rule.id"
          to="/bangumi"
          class="page-home__rule"
        >
          <img
            v-if="rule.poster_link"
            :src="rule.poster_link"
            :alt="rule.official_title || rule.rule_name"
          />
          <span v-else class="page-home__poster-placeholder" aria-hidden="true">
            {{ (rule.official_title || rule.rule_name).slice(0, 1) }}
          </span>
          <span class="page-home__rule-copy">
            <strong>{{ rule.official_title || rule.rule_name }}</strong>
            <small>
              {{ rule.group_name || t('mobile.group_unknown') }} · S{{
                String(rule.season).padStart(2, '0')
              }}
            </small>
          </span>
          <ab-tag
            v-if="rule.needs_review"
            type="warning"
            :title="t('mobile.review')"
          />
        </RouterLink>
      </div>
      <p v-else class="page-home__empty">{{ t('mobile.no_active_anime') }}</p>
    </section>
  </div>
</template>

<style lang="scss" scoped>
.page-home {
  min-width: 0;
  height: 100%;
  overflow-y: auto;
  padding: 2px 2px calc(var(--layout-gap) + env(safe-area-inset-bottom, 0px));
  color: var(--color-text);
}

.page-home__header,
.page-home__status,
.page-home__section-heading,
.page-home__summary,
.page-home__rule {
  display: flex;
  align-items: center;
}

.page-home__header {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.page-home__heading {
  min-width: 0;

  h1 {
    margin: 0;
    color: var(--color-text);
    font-size: 20px;
    font-weight: 650;
  }

  p {
    margin: 3px 0 0;
    color: var(--color-text-secondary);
    font-size: 13px;
  }
}

.page-home__refresh {
  display: grid;
  place-items: center;
  width: var(--touch-target);
  height: var(--touch-target);
  flex: 0 0 auto;
  color: var(--color-text-secondary);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;

  &:hover,
  &:focus-visible {
    color: var(--color-primary);
    border-color: var(--color-primary);
  }

  &:disabled {
    cursor: wait;
    opacity: 0.65;
  }
}

.page-home__status,
.page-home__summary,
.page-home__active {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.page-home__status {
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  margin-bottom: 10px;
}

.page-home__eyebrow {
  display: block;
  margin-bottom: 6px;
  color: var(--color-text-secondary);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.page-home__version {
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
}

.page-home__summaries {
  display: grid;
  gap: 8px;
}

.page-home__summary {
  gap: 12px;
  min-height: 72px;
  padding: 12px 14px;
  color: var(--color-text);
  text-decoration: none;
  transition: border-color var(--transition-fast),
    background-color var(--transition-fast);

  &:hover,
  &:focus-visible {
    background: var(--color-surface-hover);
    border-color: var(--color-primary);
  }
}

.page-home__summary-icon {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  color: var(--color-primary);
  background: var(--color-primary-light);
  border-radius: var(--radius-md);
}

.page-home__summary-copy,
.page-home__rule-copy {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;

  strong {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  small {
    color: var(--color-text-secondary);
    line-height: 1.45;
  }
}

.page-home__summary-copy > [data-value='primary'] {
  margin-left: auto;
  position: absolute;
  right: 18px;
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 650;
}

.page-home__summary {
  position: relative;
}

.page-home__attention {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-height: var(--touch-target);
  margin-top: 10px;
  padding: 11px 14px;
  color: var(--color-warning-text);
  background: var(--color-warning-bg);
  border: 1px solid var(--color-warning-border);
  border-radius: var(--radius-md);
  text-decoration: none;

  span {
    font-size: 12px;
  }
}

.page-home__active {
  margin-top: 10px;
  overflow: hidden;
}

.page-home__section-heading {
  justify-content: space-between;
  gap: 12px;
  min-height: var(--touch-target);
  padding: 10px 14px;
  border-bottom: 1px solid var(--color-border);

  h2 {
    margin: 0;
    font-size: 14px;
    font-weight: 650;
  }

  a {
    color: var(--color-primary);
    font-size: 12px;
    text-decoration: none;
  }
}

.page-home__rule-list {
  display: flex;
  flex-direction: column;
}

.page-home__rule {
  gap: 10px;
  min-height: 62px;
  padding: 8px 14px;
  color: var(--color-text);
  border-bottom: 1px solid var(--color-border);
  text-decoration: none;

  &:last-child {
    border-bottom: 0;
  }

  img,
  .page-home__poster-placeholder {
    width: 34px;
    height: 46px;
    flex: 0 0 auto;
    border-radius: var(--radius-sm);
  }

  img {
    object-fit: cover;
  }
}

.page-home__poster-placeholder {
  display: grid;
  place-items: center;
  color: var(--color-primary);
  background: var(--color-primary-light);
  font-weight: 650;
}

.page-home__empty {
  margin: 0;
  padding: 24px 14px;
  color: var(--color-text-secondary);
  font-size: 13px;
  text-align: center;
}

.is-spinning {
  animation: home-spin 800ms linear infinite;
}

@keyframes home-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .is-spinning {
    animation: none;
  }
}

@include forTablet {
  .page-home__summaries {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .page-home__summary {
    min-height: 96px;
  }
}
</style>
