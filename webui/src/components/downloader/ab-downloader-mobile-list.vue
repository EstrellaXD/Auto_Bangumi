<script lang="ts" setup>
import { Down } from '@icon-park/vue-next';
import {
  formatTorrentEta,
  formatTorrentSize,
  formatTorrentSpeed,
  torrentStateLabel,
  torrentStateType,
} from '@/utils/downloader-display';
import type { QbTorrentInfo, TorrentGroup } from '#/downloader';

const props = defineProps<{
  groups: TorrentGroup[];
  selectedHashes: string[];
}>();

const emit = defineEmits<{
  'toggle-hash': [hash: string];
  'toggle-group': [group: TorrentGroup];
}>();

const { t } = useMyI18n();
const expandedHashes = ref<Set<string>>(new Set());

function isSelected(torrent: QbTorrentInfo): boolean {
  return props.selectedHashes.includes(torrent.hash);
}

function isGroupSelected(group: TorrentGroup): boolean {
  return group.torrents.every((torrent) => isSelected(torrent));
}

function isExpanded(hash: string): boolean {
  return expandedHashes.value.has(hash);
}

function toggleDetails(hash: string): void {
  const next = new Set(expandedHashes.value);
  if (next.has(hash)) next.delete(hash);
  else next.add(hash);
  expandedHashes.value = next;
}
</script>

<template>
  <div class="downloader-mobile-list">
    <section v-for="group in groups" :key="group.savePath" class="mobile-group">
      <header class="mobile-group__header">
        <div class="mobile-group__summary">
          <h2 class="mobile-group__title">{{ group.name }}</h2>
          <span class="mobile-group__meta">
            {{ group.count }} {{ $t('common.items') }} ·
            {{ Math.round(group.overallProgress * 100) }}%
          </span>
        </div>
        <button
          type="button"
          class="mobile-group__select"
          :aria-label="`${
            isGroupSelected(group)
              ? $t('homepage.torrents.deselect_all')
              : $t('homepage.torrents.select_all')
          }: ${group.name}`"
          :aria-pressed="isGroupSelected(group)"
          @click="emit('toggle-group', group)"
        >
          {{
            isGroupSelected(group)
              ? $t('homepage.torrents.deselect_all')
              : $t('homepage.torrents.select_all')
          }}
        </button>
      </header>

      <div class="mobile-group__items">
        <article
          v-for="torrent in group.torrents"
          :key="torrent.hash"
          class="mobile-torrent"
          :class="{ 'mobile-torrent--selected': isSelected(torrent) }"
        >
          <div class="mobile-torrent__header">
            <button
              type="button"
              class="mobile-torrent__select"
              :class="{
                'mobile-torrent__select--checked': isSelected(torrent),
              }"
              :aria-label="
                $t('downloader.action.select_torrent', {
                  name: torrent.name,
                })
              "
              :aria-pressed="isSelected(torrent)"
              @click="emit('toggle-hash', torrent.hash)"
            >
              <svg
                v-if="isSelected(torrent)"
                viewBox="0 0 16 16"
                width="14"
                height="14"
                aria-hidden="true"
              >
                <path
                  d="M6.5 11.5L3 8l1-1 2.5 2.5L12 4l1 1z"
                  fill="currentColor"
                />
              </svg>
            </button>

            <div class="mobile-torrent__summary">
              <h3 class="mobile-torrent__name">{{ torrent.name }}</h3>
              <div class="mobile-torrent__state">
                <ab-tag
                  :type="torrentStateType(torrent.state)"
                  :title="torrentStateLabel(torrent.state, t)"
                />
              </div>
            </div>

            <button
              type="button"
              class="mobile-torrent__expand"
              :class="{
                'mobile-torrent__expand--open': isExpanded(torrent.hash),
              }"
              :aria-label="`${$t(
                isExpanded(torrent.hash)
                  ? 'downloader.action.hide_details'
                  : 'downloader.action.show_details'
              )}: ${torrent.name}`"
              :aria-expanded="isExpanded(torrent.hash)"
              :aria-controls="`torrent-details-${torrent.hash}`"
              @click="toggleDetails(torrent.hash)"
            >
              <Down :size="16" aria-hidden="true" />
            </button>
          </div>

          <ab-progress
            class="mobile-torrent__progress"
            :value="torrent.progress * 100"
            :label="`${Math.round(torrent.progress * 100)}%`"
            :aria-label="`${torrent.name}: ${$t(
              'downloader.torrent.progress'
            )}`"
            :state="
              torrent.state === 'error' || torrent.state === 'missingFiles'
                ? 'error'
                : 'active'
            "
          />

          <dl
            v-if="isExpanded(torrent.hash)"
            :id="`torrent-details-${torrent.hash}`"
            class="mobile-torrent__details"
          >
            <div>
              <dt>{{ $t('downloader.torrent.size') }}</dt>
              <dd>{{ formatTorrentSize(torrent.size) }}</dd>
            </div>
            <div>
              <dt>{{ $t('downloader.torrent.dlspeed') }}</dt>
              <dd>{{ formatTorrentSpeed(torrent.dlspeed) }}</dd>
            </div>
            <div>
              <dt>{{ $t('downloader.torrent.upspeed') }}</dt>
              <dd>{{ formatTorrentSpeed(torrent.upspeed) }}</dd>
            </div>
            <div>
              <dt>{{ $t('downloader.torrent.eta') }}</dt>
              <dd>{{ formatTorrentEta(torrent.eta) }}</dd>
            </div>
            <div>
              <dt>{{ $t('downloader.torrent.peers') }}</dt>
              <dd>{{ torrent.num_seeds }} / {{ torrent.num_leechs }}</dd>
            </div>
            <div class="mobile-torrent__path">
              <dt>{{ $t('downloader.torrent.save_path') }}</dt>
              <dd>{{ torrent.save_path }}</dd>
            </div>
          </dl>
        </article>
      </div>
    </section>
  </div>
</template>

<style lang="scss" scoped>
.downloader-mobile-list {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 12px;
}

.mobile-group {
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.mobile-group__header {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
  padding: 8px 8px 8px 12px;
  border-bottom: 1px solid var(--color-border);
}

.mobile-group__summary {
  min-width: 0;
  flex: 1;
}

.mobile-group__title,
.mobile-torrent__name {
  margin: 0;
  overflow: hidden;
  color: var(--color-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mobile-group__title {
  font-size: 14px;
  font-weight: 600;
}

.mobile-group__meta {
  display: block;
  margin-top: 2px;
  color: var(--color-text-secondary);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.mobile-group__select,
.mobile-torrent__select,
.mobile-torrent__expand {
  display: inline-flex;
  min-width: var(--touch-target);
  min-height: var(--touch-target);
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  font: inherit;

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: -2px;
  }
}

.mobile-group__select {
  padding: 0 10px;
  background: var(--color-surface-2);
  color: var(--color-text);
  font-size: 13px;
}

.mobile-group__items {
  display: flex;
  flex-direction: column;
}

.mobile-torrent {
  min-width: 0;
  padding: 8px;
  border-left: 3px solid transparent;

  & + & {
    border-top: 1px solid var(--color-border);
  }

  &--selected {
    border-left-color: var(--color-primary);
    background: color-mix(in srgb, var(--color-primary) 7%, transparent);
  }
}

.mobile-torrent__header {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 6px;
}

.mobile-torrent__select {
  position: relative;

  &::before {
    width: 20px;
    height: 20px;
    border: 2px solid var(--color-border-hover);
    border-radius: 5px;
    content: '';
  }

  svg {
    position: absolute;
    color: var(--color-white);
  }

  &--checked::before {
    border-color: var(--color-primary);
    background: var(--color-primary);
  }
}

.mobile-torrent__summary {
  min-width: 0;
  flex: 1;
}

.mobile-torrent__name {
  font-size: 13px;
  font-weight: 550;
}

.mobile-torrent__state {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
  margin-top: 5px;
  color: var(--color-text-secondary);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.mobile-torrent__expand {
  transition: color var(--transition-fast);

  svg {
    transition: transform var(--transition-fast);
  }

  &--open svg {
    transform: rotate(180deg);
  }
}

.mobile-torrent__progress {
  padding: 4px 8px 2px 50px;
}

.mobile-torrent__details {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 12px;
  margin: 8px 8px 2px 50px;
  padding-top: 10px;
  border-top: 1px solid var(--color-border);

  div {
    min-width: 0;
  }

  dt {
    color: var(--color-text-secondary);
    font-size: 11px;
  }

  dd {
    margin: 2px 0 0;
    overflow-wrap: anywhere;
    color: var(--color-text);
    font-family: var(--font-mono);
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }
}

.mobile-torrent__path {
  grid-column: 1 / -1;
}

@media (prefers-reduced-motion: reduce) {
  .mobile-torrent__expand,
  .mobile-torrent__expand svg {
    transition: none;
  }
}
</style>
