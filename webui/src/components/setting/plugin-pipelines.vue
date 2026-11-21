<script lang="ts" setup>
import { Info } from '@lucide/vue';
import AbButton from '../basic/ab-button.vue';
import AbField from '../basic/ab-field.vue';
import AbSelect from '../basic/ab-select.vue';
import AbTooltip from '../basic/ab-tooltip.vue';
import { apiPlugins } from '@/api/plugins';
import { pluginSetVersion, refreshPluginState } from '@/hooks/usePluginRefresh';

const emit = defineEmits<{ updated: [] }>();
const { t } = useMyI18n();
const store = useConfigStore();
const providers = ref<{
  organizer?: string[];
  'download.preflight'?: string[];
}>({});
const organizer = ref(store.config.plugins.slots.organizer ?? 'native');
const preflight = ref(store.config.plugins.slots.download_preflight ?? '');
const busy = ref(false);
async function loadProviders() {
  providers.value = await apiPlugins.providers();
}
onMounted(loadProviders);
watch(pluginSetVersion, loadProviders);
const dirty = computed(
  () =>
    organizer.value !== (store.config.plugins.slots.organizer ?? 'native') ||
    preflight.value !== (store.config.plugins.slots.download_preflight ?? '')
);
function options(
  point: 'organizer' | 'download.preflight',
  value: string,
  base: string,
  label: string
) {
  return [
    { value: base, label },
    ...[
      ...new Set([
        ...(providers.value[point] ?? []),
        ...(value !== base ? [value] : []),
      ]),
    ].map((id) => ({ value: id, label: id })),
  ];
}
async function save() {
  busy.value = true;
  try {
    await apiPlugins.pipelines({
      organizer: organizer.value,
      download_preflight: preflight.value,
    });
    await refreshPluginState();
    emit('updated');
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <section class="pipelines">
    <AbTooltip :content="t('config.plugins_set.pipeline_hint')">
      <button type="button" :aria-label="t('config.plugins_set.pipeline_hint')">
        <Info :size="16" />
      </button>
    </AbTooltip>
    <AbField :label="t('config.plugins_set.organizer')">
      <AbSelect
        v-model="organizer"
        :disabled="busy"
        :options="
          options(
            'organizer',
            organizer,
            'native',
            t('config.plugins_set.native')
          )
        "
      />
    </AbField>
    <AbField :label="t('config.plugins_set.preflight')">
      <AbSelect
        v-model="preflight"
        :disabled="busy"
        :options="
          options(
            'download.preflight',
            preflight,
            '',
            t('config.plugins_set.none')
          )
        "
      />
    </AbField>
    <AbButton size="sm" :loading="busy" :disabled="!dirty" @click="save">
      {{ t('config.plugins_set.save') }}
    </AbButton>
  </section>
</template>

<style scoped>
.pipelines {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: var(--layout-padding);
  display: grid;
  gap: 12px;
}
button {
  color: var(--color-text-secondary);
  justify-self: end;
}
</style>
