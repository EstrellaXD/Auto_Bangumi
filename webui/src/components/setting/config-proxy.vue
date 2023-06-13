<script lang="ts" setup>
import { useI18n } from 'vue-i18n';
import type { Proxy, ProxyType } from '#/config';
import type { SettingItem } from '#/components';

const { t } = useI18n({ useScope: 'global' });
const { getSettingGroup } = useConfigStore();

const proxy = getSettingGroup('proxy');
const proxyType: ProxyType = ['http', 'https', 'socks5'];

const items: SettingItem<Proxy>[] = [
  {
    configKey: 'enable',
    label: t('config.proxyset.enable'),
    type: 'switch',
  },
  {
    configKey: 'type',
    label: t('config.proxyset.type'),
    type: 'select',
    prop: {
      items: proxyType,
    },
    bottomLine: true,
  },
  {
    configKey: 'host',
    label: t('config.proxyset.host'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: '127.0.0.1',
    },
  },
  {
    configKey: 'port',
    label: t('config.proxyset.port'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: '7890',
    },
  },
  {
    configKey: 'username',
    label: t('config.proxyset.username'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'username',
    },
  },
  {
    configKey: 'password',
    label: t('config.proxyset.password'),
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'password',
    },
  },
];
</script>

<template>
  <ab-fold-panel :title="$t('config.proxyset.title')">
    <div space-y-12px>
      <ab-setting
        v-for="i in items"
        :key="i.configKey"
        v-bind="i"
        v-model:data="proxy[i.configKey]"
      ></ab-setting>
    </div>
  </ab-fold-panel>
</template>
