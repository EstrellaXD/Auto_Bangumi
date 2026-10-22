<script lang="ts" setup>
import { useConfirm } from '@/hooks/useConfirm';
import { countLogLevels, parseLogLines } from '@/utils/log-parse';
import type { LogLevel } from '@/utils/log-parse';

definePage({
  name: 'Log',
});

const { t } = useMyI18n();
const { onUpdate, offUpdate, reset, copy, getLog } = useLogStore();
const { confirm } = useConfirm();

async function onReset() {
  const ok = await confirm({
    title: t('log.reset'),
    body: t('log.reset_confirm'),
    confirmText: t('log.reset'),
    danger: true,
  });
  if (ok) reset();
}
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

const logContainer = useTemplateRef<HTMLElement>('logContainer');

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
    watch(
      () => log.value,
      () => {
        nextTick(() => {
          backToBottom();
        });
      },
      { once: true }
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
        <ab-alert
          v-if="hasProblems"
          :type="errorCount > 0 ? 'danger' : 'warning'"
          :title="
            $t('log.health_summary', {
              errors: errorCount,
              warnings: warningCount,
            })
          "
        >
          <template #action>
            <ab-button size="sm" @click="jumpToFirstProblem">
              {{ $t('log.jump_first') }} ↓
            </ab-button>
          </template>
        </ab-alert>

        <div class="log-viewer-card">
          <div class="log-toolbar">
            <div
              class="filter-chips"
              role="group"
              :aria-label="$t('log.filter_level')"
            >
              <ab-button
                v-for="level in logLevels"
                :key="level"
                size="sm"
                class="filter-chip"
                :variant="
                  selectedLevels.includes(level) ? 'primary' : 'secondary'
                "
                :aria-pressed="selectedLevels.includes(level)"
                @click="toggleLevel(level)"
              >
                {{ level }}
                <span class="chip-count">{{ levelCounts[level] }}</span>
              </ab-button>
            </div>

            <ab-input
              v-model="searchQuery"
              class="log-search"
              type="search"
              :placeholder="$t('log.search_placeholder')"
              :aria-label="$t('log.search_placeholder')"
            />

            <div class="log-actions">
              <ab-button size="sm" @click="getLog(true)">
                {{ $t('log.update_now') }}
              </ab-button>

              <ab-button size="sm" @click="copy">
                {{ $t('log.copy') }}
              </ab-button>

              <ab-button size="sm" variant="danger" @click="onReset">
                {{ $t('log.reset') }}
              </ab-button>
            </div>
          </div>

          <div ref="logContainer" class="log-viewer">
            <div v-if="filteredLog.length === 0" class="log-empty">
              <template v-if="formatLog.length > 0 && isFiltered">
                <p>{{ $t('log.filtered_empty') }}</p>
                <ab-button size="sm" @click="clearFilters">
                  {{ $t('log.clear_filters') }}
                </ab-button>
              </template>
              <p v-else>
                {{ $t('log.empty') }}
              </p>
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
                <span
                  class="log-level"
                  :class="`level-${i.type.toLowerCase()}`"
                >
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
              >GitHub <span aria-hidden="true">↗</span></a>
            </li>
            <li>
              <a href="https://autobangumi.org" target="_blank" rel="noopener">{{ $t('log.website') }} <span aria-hidden="true">↗</span></a>
            </li>
            <li>
              <a href="https://t.me/autobangumi" target="_blank" rel="noopener">{{ $t('log.telegram_group') }}
                <span aria-hidden="true">↗</span></a>
            </li>
            <li>
              <a
                href="https://twitter.com/Estrella_Pan"
                target="_blank"
                rel="noopener"
              >X <span aria-hidden="true">↗</span></a>
            </li>
            <li>
              <a
                href="https://github.com/EstrellaXD/Auto_Bangumi/issues"
                target="_blank"
                rel="noopener"
              >{{ $t('log.report_bug') }} <span aria-hidden="true">↗</span></a>
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

// 健康摘要只有一行引导词：与右侧按钮垂直居中
.log-main > :deep(.ab-alert) {
  align-items: center;
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

// 筛选项不换行：放不下时整组单独占一行并横向滚动，
// 搜索框与操作按钮落到下一行，不出现 3+1 的零散换行
.filter-chips {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;
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

// 与同行 sm 按钮等高（ab-input 默认 34px）；窄屏时与操作按钮共用一行并占满剩余宽度
.log-toolbar .log-search {
  flex: 1 1 100px;
  min-width: 0;
  height: 28px;

  @include forDesktop {
    max-width: 260px;
  }

  @include forTouch {
    height: var(--touch-target);
  }
}

.log-actions {
  display: flex;
  gap: 6px;
  margin-left: auto;
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

// 级别：方块语义标记 + 墨色文字（与 ab-tag 一致），不用着色填充
.log-level {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--color-text-secondary);

  &::before {
    content: '';
    width: 7px;
    height: 7px;
    border-radius: 2px;
    flex-shrink: 0;
    background: var(--color-text-muted);
  }

  &.level-debug::before {
    background: transparent;
    box-shadow: inset 0 0 0 1px var(--color-text-muted);
  }

  &.level-warning::before {
    background: var(--color-warning);
  }

  &.level-error::before {
    background: var(--color-danger);
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
