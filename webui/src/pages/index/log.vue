<script lang="ts" setup>
import { NButton, NPopconfirm } from 'naive-ui';
import { watchOnce } from '@vueuse/core';
import { countLogLevels, parseLogLines } from '@/utils/log-parse';
import type { LogLevel } from '@/utils/log-parse';

definePage({
  name: 'Log',
});

const { onUpdate, offUpdate, reset, copy, getLog } = useLogStore();
const { log } = storeToRefs(useLogStore());

// Filter states
const selectedLevels = ref<string[]>([]);
const searchQuery = ref('');

// Log levels
const logLevels: LogLevel[] = ['INFO', 'WARNING', 'ERROR', 'DEBUG'];

// Rendering is unvirtualized, so bound the work: only the newest lines are
// parsed and shown. Older history is still available via the log file.
const MAX_LOG_LINES = 1000;

const formatLog = computed(() => parseLogLines(log.value, MAX_LOG_LINES));

const levelCounts = computed(() => countLogLevels(formatLog.value));

// 健康摘要：错误/警告计数，回答“是否在正常工作”
const errorCount = computed(() => levelCounts.value.ERROR);
const warningCount = computed(() => levelCounts.value.WARNING);
const hasProblems = computed(() => errorCount.value + warningCount.value > 0);

// Filtered logs based on selected levels + text search
const filteredLog = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  return formatLog.value.filter((entry) => {
    if (
      selectedLevels.value.length > 0 &&
      !selectedLevels.value.includes(entry.type)
    ) {
      return false;
    }
    if (
      query &&
      !entry.content.toLowerCase().includes(query) &&
      !entry.module.toLowerCase().includes(query)
    ) {
      return false;
    }
    return true;
  });
});

const isFiltered = computed(
  () => selectedLevels.value.length > 0 || searchQuery.value.trim() !== ''
);

// Toggle level filter
function toggleLevel(level: string) {
  const index = selectedLevels.value.indexOf(level);
  if (index === -1) {
    selectedLevels.value.push(level);
  } else {
    selectedLevels.value.splice(index, 1);
  }
}

// Clear all filters
function clearFilters() {
  selectedLevels.value = [];
  searchQuery.value = '';
}

const logContainer = ref<HTMLElement | null>(null);

function scrollBehavior(): ScrollBehavior {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ? 'auto'
    : 'smooth';
}

function backToBottom() {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight;
  }
}

function jumpToFirstProblem() {
  const el = logContainer.value?.querySelector<HTMLElement>(
    '.log-entry.is-error, .log-entry.is-warning'
  );
  el?.scrollIntoView({ behavior: scrollBehavior(), block: 'center' });
}

onActivated(() => {
  onUpdate();

  if (log.value) {
    backToBottom();
  } else {
    // SSE 只在日志变化时推送：新会话首次进入时主动拉一次全量日志
    getLog(true);
    watchOnce(
      () => log.value,
      () => {
        nextTick(() => {
          backToBottom();
        });
      }
    );
  }
});

onDeactivated(() => {
  offUpdate();
});
</script>

<template>
  <div class="page-log">
    <div class="log-layout">
      <div class="log-main">
        <div
          v-if="hasProblems"
          class="log-health"
          :class="{ 'has-errors': errorCount > 0 }"
          role="status"
        >
          <b>{{
            $t('log.health_summary', {
              errors: errorCount,
              warnings: warningCount,
            })
          }}</b>
          <NButton size="tiny" secondary @click="jumpToFirstProblem">
            {{ $t('log.jump_first') }} ↓
          </NButton>
        </div>

        <div class="log-viewer-card">
          <div class="log-toolbar">
            <div
              class="filter-chips"
              role="group"
              :aria-label="$t('log.filter_level')"
            >
              <NButton
                v-for="level in logLevels"
                :key="level"
                size="small"
                class="filter-chip"
                :secondary="!selectedLevels.includes(level)"
                :type="selectedLevels.includes(level) ? 'primary' : 'default'"
                :aria-pressed="selectedLevels.includes(level)"
                @click="toggleLevel(level)"
              >
                {{ level }}
                <span class="chip-count">{{ levelCounts[level] }}</span>
              </NButton>
            </div>

            <input
              v-model="searchQuery"
              ab-input
              class="log-search"
              type="search"
              :placeholder="$t('log.search_placeholder')"
              :aria-label="$t('log.search_placeholder')"
            />

            <div class="log-actions">
              <NButton size="small" secondary @click="getLog(true)">
                {{ $t('log.update_now') }}
              </NButton>

              <NButton size="small" secondary @click="copy">
                {{ $t('log.copy') }}
              </NButton>

              <NPopconfirm
                :positive-text="$t('log.reset')"
                :negative-text="$t('config.cancel')"
                :positive-button-props="{ type: 'error' }"
                @positive-click="reset"
              >
                <template #trigger>
                  <NButton size="small" secondary type="error">
                    {{ $t('log.reset') }}
                  </NButton>
                </template>
                {{ $t('log.reset_confirm') }}
              </NPopconfirm>
            </div>
          </div>

          <div ref="logContainer" class="log-viewer">
            <div v-if="filteredLog.length === 0" class="log-empty">
              <template v-if="formatLog.length > 0 && isFiltered">
                <p>{{ $t('log.filtered_empty') }}</p>
                <NButton size="small" secondary @click="clearFilters">
                  {{ $t('log.clear_filters') }}
                </NButton>
              </template>
              <p v-else>{{ $t('log.empty') }}</p>
            </div>
            <div v-else class="log-content">
              <div
                v-for="i in filteredLog"
                :key="i.index"
                class="log-entry"
                :class="{
                  'is-error': i.type === 'ERROR',
                  'is-warning': i.type === 'WARNING',
                }"
              >
                <span class="log-level" :class="`level-${i.type.toLowerCase()}`">
                  {{ i.type || '—' }}
                </span>
                <span class="log-date">{{ i.date }}</span>
                <span class="log-message">
                  <span v-if="i.module" class="log-module">{{ i.module }}</span>
                  {{ i.content }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="log-sidebar">
        <ab-container :title="$t('log.about')">
          <ul class="about-links">
            <li>
              <a
                href="https://github.com/EstrellaXD/Auto_Bangumi"
                target="_blank"
                rel="noopener"
                >GitHub <span aria-hidden="true">↗</span></a
              >
            </li>
            <li>
              <a href="https://autobangumi.org" target="_blank" rel="noopener"
                >{{ $t('log.website') }} <span aria-hidden="true">↗</span></a
              >
            </li>
            <li>
              <a href="https://t.me/autobangumi" target="_blank" rel="noopener"
                >{{ $t('log.telegram_group') }}
                <span aria-hidden="true">↗</span></a
              >
            </li>
            <li>
              <a
                href="https://twitter.com/Estrella_Pan"
                target="_blank"
                rel="noopener"
                >X <span aria-hidden="true">↗</span></a
              >
            </li>
            <li>
              <a
                href="https://github.com/EstrellaXD/Auto_Bangumi/issues"
                target="_blank"
                rel="noopener"
                >{{ $t('log.report_bug') }} <span aria-hidden="true">↗</span></a
              >
            </li>
          </ul>
        </ab-container>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.page-log {
  overflow: auto;
  flex-grow: 1;
}

.log-layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  align-items: start;

  @include forDesktop {
    grid-template-columns: 1fr 280px;
  }
}

.log-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.log-health {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-warning-border);
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
  font-size: 13px;

  &.has-errors {
    border-color: color-mix(in srgb, var(--color-danger) 35%, transparent);
    background: color-mix(in srgb, var(--color-danger) 8%, var(--color-surface));
    color: var(--color-danger);
  }
}

.log-viewer-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  overflow: hidden;
}

.log-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--color-border);
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.filter-chip {
  @include forTouch {
    min-height: var(--touch-target);
  }
}

.chip-count {
  margin-left: 5px;
  font-size: 11px;
  opacity: 0.75;
  font-variant-numeric: tabular-nums;
}

.log-search {
  flex: 1;
  min-width: 140px;
  max-width: 260px;
}

.log-actions {
  display: flex;
  gap: 6px;
  margin-left: auto;

  :deep(.n-button) {
    @include forTouch {
      min-height: var(--touch-target);
    }
  }
}

.log-viewer {
  overflow: auto;
  max-height: 62vh;
  padding: 4px 0;
}

.log-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 24px 12px;
  text-align: center;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.log-entry {
  display: grid;
  // 固定列宽：auto 轨道会随每行徽标/时间戳宽度变化，导致跨行错位
  grid-template-columns: 64px 21ch 1fr;
  align-items: baseline;
  gap: 10px;
  padding: 4px 12px;
  line-height: 1.5;
  // 行内统一等宽字体与字号；时间戳 21ch 轨道按此字体解析
  font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  font-size: 12.5px;

  &.is-warning {
    background: color-mix(in srgb, var(--color-warning) 9%, transparent);
  }

  &.is-error {
    background: color-mix(in srgb, var(--color-danger) 8%, transparent);
  }

  @media (max-width: 639px) {
    grid-template-columns: 64px 1fr;

    .log-message {
      grid-column: 1 / -1;
    }
  }
}

.log-level {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 58px;
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.04em;

  &.level-info {
    background: var(--color-surface-hover);
    color: var(--color-text-secondary);
  }

  &.level-debug {
    background: transparent;
    border: 1px dashed var(--color-border-hover);
    color: var(--color-text-secondary);
  }

  &.level-warning {
    background: var(--color-warning-bg);
    border: 1px solid var(--color-warning-border);
    color: var(--color-warning-text);
  }

  &.level-error {
    background: color-mix(in srgb, var(--color-danger) 12%, var(--color-surface));
    border: 1px solid color-mix(in srgb, var(--color-danger) 40%, transparent);
    color: var(--color-danger);
  }
}

.log-date {
  color: var(--color-text-secondary);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.log-message {
  min-width: 0;
  color: var(--color-text);
  overflow-wrap: anywhere;
}

.log-module {
  color: var(--color-text-secondary);
  margin-right: 4px;

  &::after {
    content: '—';
    margin-left: 4px;
  }
}

.log-sidebar {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.about-links {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;

  a {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 8px 4px;
    border-radius: var(--radius-sm);
    color: var(--color-text);
    font-size: 13px;
    text-decoration: none;
    transition: background-color var(--transition-fast);

    span {
      color: var(--color-text-secondary);
    }

    &:hover {
      background: var(--color-surface-hover);
      color: var(--color-primary);
    }

    @include forTouch {
      min-height: var(--touch-target);
    }
  }

  li + li a {
    border-top: 1px solid var(--color-border);
    border-radius: 0;
  }
}
</style>
