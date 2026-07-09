<script lang="ts" setup>
import type { Security } from '#/config';
import type { SettingItem } from '#/components';
import { useMyI18n } from '@/hooks/useMyI18n';
import { useConfigStore } from '@/store/config';

const { t } = useMyI18n();
const { getSettingGroup } = useConfigStore();

const security = getSettingGroup('security');

const items: SettingItem<Security>[] = [
  {
    configKey: 'login_whitelist',
    label: () => t('config.security_set.login_whitelist'),
    type: 'dynamic-tags',
    prop: {
      placeholder: '192.168.0.0/16',
    },
  },
  {
    configKey: 'mcp_whitelist',
    label: () => t('config.security_set.mcp_whitelist'),
    type: 'dynamic-tags',
    prop: {
      placeholder: '127.0.0.0/8',
    },
  },
];
</script>

<template>
  <ab-fold-panel :title="$t('config.security_set.title')">
    <p class="hint-text">{{ $t('config.security_set.hint') }}</p>
    <div space-y-8>
      <ab-setting
        v-for="i in items"
        :key="i.configKey"
        v-bind="i"
        v-model:data="security[i.configKey]"
      ></ab-setting>
    </div>
  </ab-fold-panel>
</template>

<style lang="scss" scoped>
.hint-text {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 12px;
  line-height: 1.5;
}
</style>
