<script lang="ts" setup>
import type { Downloader, DownloaderType } from '#/config';
import type { SettingItem } from '#/components';

const { getSettingGroup } = useConfigStore();

const downloader = getSettingGroup('downloader');
const downloaderType: DownloaderType = ['qbittorrent'];

const items: SettingItem<Downloader>[] = [
  {
    configKey: 'type',
    label: 'Downloader Type',
    type: 'select',
    css: 'w-115px',
    prop: {
      items: downloaderType,
    },
  },
  {
    configKey: 'host',
    label: 'Host',
    type: 'input',
    prop: {
      type: 'text',
      placeholder: '127.0.0.1:8989',
    },
  },
  {
    configKey: 'username',
    label: 'Username',
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'admin',
    },
  },
  {
    configKey: 'password',
    label: 'Password',
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'admindmin',
    },
    bottomLine: true,
  },
  {
    configKey: 'path',
    label: 'Download Path',
    type: 'input',
    prop: {
      type: 'text',
      placeholder: '/downloads/Bangumi',
    },
  },
  {
    configKey: 'ssl',
    label: 'SSL',
    type: 'switch',
  },
];
</script>

<template>
  <ab-fold-panel title="Downloader Setting">
    <div space-y-12px>
      <ab-setting
        v-for="i in items"
        :key="i.configKey"
        v-bind="i"
        v-model:data="downloader[i.configKey]"
      ></ab-setting>
    </div>
  </ab-fold-panel>
</template>
