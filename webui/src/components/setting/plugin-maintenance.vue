<script lang="ts" setup>
import AbAlert from '../basic/ab-alert.vue';
import AbButton from '../basic/ab-button.vue';
import AbTooltip from '../basic/ab-tooltip.vue';
import { apiPlugins } from '@/api/plugins';
import type { MaintenanceOperation } from '@/api/plugins';
import { refreshPluginState } from '@/hooks/usePluginRefresh';

const { t } = useMyI18n();
const operations = ref<MaintenanceOperation[]>([]);
const busy = ref(false);
async function load() {
  operations.value = await apiPlugins.maintenance();
}
onMounted(load);
defineExpose({ load });
async function recover(operation: MaintenanceOperation) {
  busy.value = true;
  try {
    await apiPlugins.recoverMaintenance(operation);
    await refreshPluginState();
    await load();
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <AbAlert
    v-if="operations.length"
    type="warning"
    :title="t('config.plugins_set.recovery')"
  >
    <div v-for="operation in operations" :key="operation.id">
      <AbTooltip :content="operation.backup_path">
        <span
          >{{ operation.owner }} · {{ operation.step }} ·
          {{ operation.error }}</span
        >
      </AbTooltip>
      <AbTooltip :content="t('config.plugins_set.recovery_hint')">
        <AbButton size="sm" :loading="busy" @click="recover(operation)">
          {{
            t(
              operation.name === 'local-plugin-update' &&
                ['replacing-code', 'loaded'].includes(operation.step)
                ? 'config.plugins_set.restore_code'
                : 'config.plugins_set.acknowledge'
            )
          }}
        </AbButton>
      </AbTooltip>
    </div>
    <AbButton size="sm" @click="load">
      {{ t('config.plugins_set.refresh_status') }}
    </AbButton>
  </AbAlert>
</template>
