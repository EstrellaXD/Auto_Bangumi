<script lang="ts" setup>
import type { Downloader, DownloaderType } from '#/config';
import type { SettingItem } from '#/components';
import { ref, onMounted } from 'vue';
import { apiProgram } from '@/api/program';

const { t } = useMyI18n();
const { getSettingGroup } = useConfigStore();

const downloader = getSettingGroup('downloader');
const downloaderType: DownloaderType = ['qbittorrent'];

const platform = ref<string>('linux');

onMounted(async () => {
  try {
    const status = await apiProgram.status();
    platform.value = status.platform;
  } catch {
    platform.value = 'linux';
  }
});

function convertPath() {
  const current = downloader.path as string;
  if (!current) return;
  if (platform.value === 'linux') {
    const winPath = current.replace(/^\/downloads\//, 'D:\\').replace(/\//g, '\\');
    if (winPath !== current) {
      downloader.path = winPath;
    }
  } else {
    const linuxPath = current.replace(/^[A-Za-z]:\\/, '/downloads/').replace(/\\/g, '/');
    if (linuxPath !== current) {
      downloader.path = linuxPath;
    }
  }
}

const items: SettingItem<Downloader>[] = [
  {
    configKey: 'type',
    label: () => t('config.downloader_set.type'),
    type: 'select',
    css: 'w-115',
    prop: {
      items: downloaderType,
    },
  },
  {
    configKey: 'host',
    label: () => t('config.downloader_set.host'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: '127.0.0.1:8989',
    },
  },
  {
    configKey: 'username',
    label: () => t('config.downloader_set.username'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'admin',
    },
  },
  {
    configKey: 'password',
    label: () => t('config.downloader_set.password'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'admindmin',
    },
    bottomLine: true,
  },
  {
    configKey: 'path',
    label: () => t('config.downloader_set.path'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: '/downloads/Bangumi',
    },
  },
  {
    configKey: 'ssl',
    label: () => t('config.downloader_set.ssl'),
    type: 'switch',
  },
];
</script>

<template>
  <ab-fold-panel :title="$t('config.downloader_set.title')">
    <div space-y-8>
      <ab-setting
        v-for="i in items"
        :key="i.configKey"
        v-bind="i"
        v-model:data="downloader[i.configKey]"
      ></ab-setting>
      <div class="convert-bar">
        <span class="convert-label">{{ $t('config.downloader_set.path') }}</span>
        <div class="convert-actions">
          <span class="platform-badge">{{ platform === 'linux' ? 'Linux/Docker' : 'Windows' }}</span>
          <button class="convert-btn" @click="convertPath">
            路径转换 &rarr;
          </button>
        </div>
      </div>
    </div>
  </ab-fold-panel>
</template>

<style scoped>
.convert-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--el-color-info-light-9);
  border-radius: 6px;
  font-size: 13px;
  margin-top: 8px;
}
.convert-label {
  color: var(--el-text-color-secondary);
}
.convert-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.platform-badge {
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 500;
}
.convert-btn {
  padding: 4px 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: var(--el-bg-color);
  color: var(--el-text-color-primary);
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}
.convert-btn:hover {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}
</style>
