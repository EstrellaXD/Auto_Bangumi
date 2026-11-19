<script lang="ts" setup>
import { Info } from '@lucide/vue';
import AbButton from '../basic/ab-button.vue';
import AbField from '../basic/ab-field.vue';
import AbInput from '../basic/ab-input.vue';
import AbTag from '../basic/ab-tag.vue';
import AbTooltip from '../basic/ab-tooltip.vue';
import type { PluginInfo } from '#/plugins';
import { apiPlugins } from '@/api/plugins';
import { refreshPluginState } from '@/hooks/usePluginRefresh';

const props = defineProps<{ plugin: PluginInfo; allowUnsigned: boolean }>();
const emit = defineEmits<{ updated: [] }>();
const { t } = useMyI18n();
const repository = ref(props.plugin.local_source ?? '');
const busy = ref(false);
const update = ref<{ version: string; available: boolean } | null>(null);
watch(() => props.plugin.local_source, (value) => {
  repository.value = value ?? '';
});
onMounted(async () => {
  if (props.allowUnsigned && props.plugin.local_source) update.value = await apiPlugins.localUpdate(props.plugin.id);
});
async function act(action: () => Promise<unknown>) {
  busy.value = true;
  try {
    await action();
  } finally {
    busy.value = false;
    emit('updated');
  }
}
async function save() {
  await apiPlugins.localSource(props.plugin.id, repository.value.trim());
  update.value = null;
  await refreshPluginState();
  emit('updated');
}
async function check() {
  update.value = await apiPlugins.checkLocalUpdate(props.plugin.id);
}
async function install() {
  // 每次点击固定本次来源、版本、校验和；不复用过期的界面 token。
  const fresh = await apiPlugins.checkLocalUpdate(props.plugin.id);
  update.value = fresh;
  if (!fresh.available) return;
  await apiPlugins.installLocalUpdate(props.plugin.id, fresh.version, fresh.install_token);
  update.value = null;
  await refreshPluginState();
  emit('updated');
}
</script>

<template>
  <div class="local-update">
    <AbField :label="t('config.plugins_set.update_source')">
      <AbInput v-model="repository" :disabled="busy || !allowUnsigned" placeholder="owner/repo" />
    </AbField>
    <div class="actions">
      <AbTooltip :content="t('config.plugins_set.update_hint')">
        <button type="button" :aria-label="t('config.plugins_set.update_hint')">
          <Info :size="16" />
        </button>
      </AbTooltip>
      <AbButton size="sm" :loading="busy" :disabled="!allowUnsigned || repository.trim() === (plugin.local_source ?? '')" @click="act(save)">
        {{ t('config.plugins_set.save_source') }}
      </AbButton>
      <AbButton v-if="plugin.local_source" size="sm" :disabled="busy || !allowUnsigned" @click="act(check)">
        {{ t('config.plugins_set.check_update') }}
      </AbButton>
      <AbButton v-if="update?.available" size="sm" variant="primary" :loading="busy" :disabled="!allowUnsigned" @click="act(install)">
        {{ t('config.plugins_set.apply_update', { version: update.version }) }}
      </AbButton>
      <AbTag v-else-if="update">
        {{ t('config.plugins_set.up_to_date') }}
      </AbTag>
    </div>
  </div>
</template>

<style scoped>
.local-update { display: grid; gap: 8px; }
.actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
button { color: var(--color-text-secondary); }
</style>
