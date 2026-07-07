<script lang="ts" setup>
import { Info } from '@icon-park/vue-next';
import type { Downloader, DownloaderType } from '#/config';
import type { SettingItem } from '#/components';

const { t } = useMyI18n();
const { getSettingGroup } = useConfigStore();

const downloader = getSettingGroup('downloader');
const downloaderType: DownloaderType = ['qbittorrent', 'aria2'];

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
      placeholder: '127.0.0.1:8080',
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
      type: 'password',
      autocomplete: 'off',
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
      <div v-if="downloader.type === 'aria2'" class="downloader-hint">
        <Info size="16" />
        <span>{{ $t('config.downloader_set.aria2_hint') }}</span>
      </div>

      <ab-setting
        v-for="i in items"
        :key="i.configKey"
        v-bind="i"
        v-model:data="downloader[i.configKey]"
      ></ab-setting>
    </div>
  </ab-fold-panel>
</template>

<style lang="scss" scoped>
.downloader-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-primary) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-primary) 25%, transparent);
  color: var(--color-text-secondary);
  font-size: 12px;
  transition:
    background-color var(--transition-normal),
    border-color var(--transition-normal);
}
</style>
