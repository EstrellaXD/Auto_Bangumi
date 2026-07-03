<script lang="ts" setup>
import { NButton, NPopconfirm } from 'naive-ui';
import { watchOnce } from '@vueuse/core';

definePage({
  name: 'Log',
});

const { onUpdate, offUpdate, reset, copy, getLog } = useLogStore();
const { log } = storeToRefs(useLogStore());
const { version } = useAppInfo();

// Filter states
const selectedLevels = ref<string[]>([]);

// Log levels
const logLevels = ['INFO', 'WARNING', 'ERROR', 'DEBUG'];

// Rendering is unvirtualized, so bound the work: only the newest lines are
// parsed and shown. Older history is still available via the log file.
const MAX_LOG_LINES = 1000;

const formatLog = computed(() => {
  const list = log.value
    .trim()
    .split('\n')
    .filter((i) => i !== '');
  const startIndex = list.findIndex((i) => /Version/.test(i));

  return list
    .slice(startIndex === -1 ? 0 : startIndex)
    .slice(-MAX_LOG_LINES)
    .map((i, index) => {
      const date = i.match(/\[\d+-\d+-\d+\ \d+:\d+:\d+\]/)?.[0] || '';
      const type = i.match(/(INFO)|(WARNING)|(ERROR)|(DEBUG)/)?.[0] || '';
      const content = i.replace(date, '').replace(`${type}:`, '').trim();

      return {
        index,
        date,
        type,
        content,
      };
    });
});

// Filtered logs based on selected levels
const filteredLog = computed(() => {
  if (selectedLevels.value.length === 0) {
    return formatLog.value;
  }
  return formatLog.value.filter((entry) =>
    selectedLevels.value.includes(entry.type)
  );
});

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
}

function typeColor(type: string) {
  const M: Record<string, string> = {
    INFO: 'var(--color-primary)',
    WARNING: 'var(--color-warning)',
    ERROR: 'var(--color-danger)',
    DEBUG: 'var(--color-text-muted)',
  };
  return M[type] || 'var(--color-text)';
}

const logContainer = ref<HTMLElement | null>(null);

function backToBottom() {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight;
  }
}

onActivated(() => {
  onUpdate();

  if (log.value) {
    backToBottom();
  } else {
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
      <ab-container :title="$t('log.title')" class="log-main">
        <!-- Level Filter Section -->
        <div class="log-filters">
          <div class="filter-group">
            <span class="filter-label">{{ $t('log.filter_level') }}</span>
            <div class="filter-chips">
              <button
                v-for="level in logLevels"
                :key="level"
                class="filter-chip"
                :class="{
                  active: selectedLevels.includes(level),
                  [`level-${level.toLowerCase()}`]: true,
                }"
                @click="toggleLevel(level)"
              >
                {{ level }}
              </button>
            </div>
          </div>

          <button
            v-if="selectedLevels.length > 0"
            class="clear-filters"
            @click="clearFilters"
          >
            {{ $t('log.clear_filters') }}
          </button>
        </div>

        <div ref="logContainer" class="log-viewer">
          <div v-if="filteredLog.length === 0" class="log-empty">
            {{ $t('log.empty') }}
          </div>
          <div v-else class="log-content">
            <template v-for="i in filteredLog" :key="i.index">
              <div class="log-entry" :style="{ color: typeColor(i.type) }">
                <div class="log-meta">
                  <div class="log-type">{{ i.type }}</div>
                  <div class="log-date">{{ i.date }}</div>
                </div>
                <div class="log-message">{{ i.content }}</div>
              </div>
            </template>
          </div>
        </div>

        <div class="log-actions">
          <NButton type="primary" size="small" @click="getLog">
            {{ $t('log.update_now') }}
          </NButton>

          <NPopconfirm
            :positive-text="$t('log.reset')"
            :negative-text="$t('config.cancel')"
            :positive-button-props="{ type: 'error' }"
            @positive-click="reset"
          >
            <template #trigger>
              <NButton type="error" size="small">
                {{ $t('log.reset') }}
              </NButton>
            </template>
            {{ $t('log.reset_confirm') }}
          </NPopconfirm>

          <NButton type="primary" size="small" @click="copy">
            {{ $t('log.copy') }}
          </NButton>
        </div>
      </ab-container>

      <div class="log-sidebar">
        <update-card />

        <ab-container :title="$t('log.contact_info')">
          <div class="contact-list">
            <ab-label label="Github">
              <NButton
                type="primary"
                size="small"
                tag="a"
                href="https://github.com/EstrellaXD/Auto_Bangumi"
                target="_blank"
              >
                {{ $t('log.go') }}
              </NButton>
            </ab-label>

            <ab-label label="Official Website">
              <NButton
                type="primary"
                size="small"
                tag="a"
                href="https://autobangumi.org"
                target="_blank"
              >
                {{ $t('log.go') }}
              </NButton>
            </ab-label>

            <div class="divider"></div>

            <ab-label label="X">
              <NButton
                type="primary"
                size="small"
                tag="a"
                href="https://twitter.com/Estrella_Pan"
                target="_blank"
              >
                {{ $t('log.go') }}
              </NButton>
            </ab-label>

            <ab-label label="Telegram Group">
              <NButton
                type="primary"
                size="small"
                tag="a"
                href="https://t.me/autobangumi"
                target="_blank"
              >
                {{ $t('log.join') }}
              </NButton>
            </ab-label>
          </div>
        </ab-container>

        <ab-container :title="$t('log.bug_repo')">
          <div class="bug-section">
            <NButton
              type="primary"
              class="issues-btn"
              tag="a"
              href="https://github.com/EstrellaXD/Auto_Bangumi/issues"
            >
              Github Issues
            </NButton>

            <div class="divider"></div>

            <div class="version-info">
              <span>Version: </span>
              <span>{{ version }}</span>
            </div>
          </div>
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
    grid-template-columns: 3fr 2fr;
  }
}

.log-main {
  min-width: 0;
}

.log-viewer {
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  overflow: auto;
  padding: 10px;
  max-height: 60vh;
  transition: border-color var(--transition-normal);
}

.log-content {
  min-width: 0;
}

.log-empty {
  padding: 24px 12px;
  text-align: center;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.log-entry {
  padding: 10px 0;
  line-height: 1.5;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: flex-start;
  gap: 12px;

  @include forDesktop {
    align-items: center;
    gap: 20px;
  }

  &:last-child {
    border-bottom: none;
  }
}

.log-meta {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
}

.log-type {
  text-align: center;
  font-weight: 500;
  font-size: 12px;
}

.log-date {
  font-size: 11px;
  opacity: 0.8;
}

.log-message {
  flex: 1;
  word-break: break-all;
  font-size: 13px;
}

.log-filters {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border);
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;

  @include forDesktop {
    flex-direction: row;
    align-items: center;
  }
}

.filter-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-muted);
  min-width: 60px;
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.filter-chip {
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: transparent;
  font-size: 12px;
  cursor: pointer;
  transition: all var(--transition-fast);
  color: var(--color-text);

  @include forTouch {
    min-height: 40px;
    padding: 4px 16px;
  }

  &:hover {
    border-color: var(--color-primary);
  }

  &.active {
    background: var(--color-primary);
    border-color: var(--color-primary);
    color: white;
  }

  &.level-info {
    &:hover,
    &.active {
      border-color: var(--color-primary);
    }
    &.active {
      background: var(--color-primary);
    }
  }

  &.level-warning {
    &:hover,
    &.active {
      border-color: var(--color-warning);
    }
    &.active {
      background: var(--color-warning);
    }
  }

  &.level-error {
    &:hover,
    &.active {
      border-color: var(--color-danger);
    }
    &.active {
      background: var(--color-danger);
    }
  }

  &.level-debug {
    &:hover,
    &.active {
      border-color: var(--color-text-muted);
    }
    &.active {
      background: var(--color-text-muted);
    }
  }
}

.clear-filters {
  align-self: flex-start;
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  border: none;
  background: var(--color-danger-light);
  color: var(--color-danger);
  font-size: 12px;
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--color-danger);
    color: white;
  }
}

.log-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 12px;
}

.log-sidebar {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.contact-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.divider {
  width: 100%;
  height: 1px;
  background: var(--color-border);
}

.bug-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
}

.issues-btn {
  width: 100%;
  max-width: 300px;
  height: 46px;
  font-size: 16px;
  border-radius: var(--radius-md);
}

.version-info {
  text-align: center;
  color: var(--color-primary);
  font-size: 16px;
}
</style>
