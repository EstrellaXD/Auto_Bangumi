<script lang="ts" setup>
import type { Proxy, ProxyType } from '#/config';
import type { SettingItem } from '#/components';

const { getSettingGroup } = useConfigStore();

const proxy = getSettingGroup('proxy');
const proxyType: ProxyType = ['http', 'https', 'socks5'];

const items: SettingItem<Proxy>[] = [
  {
    configKey: 'enable',
    label: 'Enable',
    type: 'switch',
  },
  {
    configKey: 'type',
    label: 'Proxy Type',
    type: 'select',
    prop: {
      items: proxyType,
    },
    bottomLine: true,
  },
  {
    configKey: 'host',
    label: 'Host',
    type: 'input',
    prop: {
      type: 'text',
      placeholder: '127.0.0.1',
    },
  },
  {
    configKey: 'port',
    label: 'Port',
    type: 'input',
    prop: {
      type: 'text',
      placeholder: '7890',
    },
  },
  {
    configKey: 'username',
    label: 'Username',
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'username',
    },
  },
  {
    configKey: 'password',
    label: 'Password',
    type: 'input',
    prop: {
      type: 'text',
      placeholder: 'password',
    },
  },
];
</script>

<template>
  <ab-fold-panel title="Proxy Setting">
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
