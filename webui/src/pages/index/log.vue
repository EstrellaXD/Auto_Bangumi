<script lang="ts" setup>
import { watchOnce } from '@vueuse/core';

definePage({
  name: 'Log',
});

const { onUpdate, offUpdate, reset, copy, getLog } = useLogStore();
const { log } = storeToRefs(useLogStore());
const { version } = useAppInfo();

const formatLog = computed(() => {
  const list = log.value
    .trim()
    .split('\n')
    .filter((i) => i !== '');
  const startIndex = list.findIndex((i) => /Version/.test(i));

  return list.slice(startIndex === -1 ? 0 : startIndex).map((i, index) => {
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
        <div ref="logContainer" class="log-viewer">
          <div class="log-content">
            <template v-for="i in formatLog" :key="i.index">
              <div
                class="log-entry"
                :style="{ color: typeColor(i.type) }"
              >
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
          <ab-button size="small" @click="getLog">
            {{ $t('log.update_now') }}
          </ab-button>

          <ab-button type="warn" size="small" @click="reset">
            {{ $t('log.reset') }}
          </ab-button>

          <ab-button size="small" @click="copy">
            {{ $t('log.copy') }}
          </ab-button>
        </div>
      </ab-container>

      <div class="log-sidebar">
        <ab-container :title="$t('log.contact_info')">
          <div class="contact-list">
            <ab-label label="Github">
              <ab-button
                size="small"
                link="https://github.com/EstrellaXD/Auto_Bangumi"
                target="_blank"
              >
                {{ $t('log.go') }}
              </ab-button>
            </ab-label>

            <ab-label label="Official Website">
              <ab-button
                size="small"
                link="https://autobangumi.org"
                target="_blank"
              >
                {{ $t('log.go') }}
              </ab-button>
            </ab-label>

            <div class="divider"></div>

            <ab-label label="X">
              <ab-button
                size="small"
                link="https://twitter.com/Estrella_Pan"
                target="_blank"
              >
                {{ $t('log.go') }}
              </ab-button>
            </ab-label>

            <ab-label label="Telegram Group">
              <ab-button
                size="small"
                link="https://t.me/autobangumi"
                target="_blank"
              >
                {{ $t('log.join') }}
              </ab-button>
            </ab-label>
          </div>
        </ab-container>

        <ab-container :title="$t('log.bug_repo')">
          <div class="bug-section">
            <ab-button
              class="issues-btn"
              link="https://github.com/EstrellaXD/Auto_Bangumi/issues"
            >
              Github Issues
            </ab-button>

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
