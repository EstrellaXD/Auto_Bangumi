<script lang="ts" setup>
import AbAlert from '../basic/ab-alert.vue';
import AbButton from '../basic/ab-button.vue';
import AbField from '../basic/ab-field.vue';
import AbSwitch from '../basic/ab-switch.vue';
import AbTag from '../basic/ab-tag.vue';
import PluginSchemaForm from './plugin-schema-form.vue';
import type { PluginInfo, PluginsOverview } from '#/plugins';
import { apiPlugins } from '@/api/plugins';
import { fillSchemaDefaults, schemaFields } from '@/utils/plugin-schema';

// 插件卡片不参与全局保存：每次改动直接调 /plugins 接口落盘并应用，
// 随后刷新 config store 的 plugins 段，避免全局保存用旧值覆盖。
const { t } = useMyI18n();
const message = useMessage();
const { refreshGroup } = useConfigStore();

const overview = ref<PluginsOverview | null>(null);
const drafts = ref<Record<string, Record<string, unknown>>>({});
const busy = ref<string | null>(null);

const stateType = {
  active: 'success',
  disabled: 'neutral',
  error: 'danger',
} as const;

function apply(data: PluginsOverview) {
  overview.value = data;
  drafts.value = Object.fromEntries(
    data.plugins.map((p) => [
      p.id,
      fillSchemaDefaults(schemaFields(p.config_schema), p.options),
    ])
  );
}

async function load() {
  try {
    apply(await apiPlugins.list());
  } catch {
    message.error(t('config.plugins_set.load_failed'));
  }
}

async function run(key: string, action: () => Promise<PluginsOverview>) {
  busy.value = key;
  try {
    apply(await action());
    await refreshGroup('plugins');
    return true;
  } catch {
    message.error(t('config.plugins_set.save_failed'));
    return false;
  } finally {
    busy.value = null;
  }
}

function setAllowUnsigned(value: boolean) {
  run('__settings', () => apiPlugins.updateSettings(value));
}

function setEnabled(plugin: PluginInfo, enabled: boolean) {
  run(plugin.id, () => apiPlugins.update(plugin.id, { enabled }));
}

async function saveOptions(plugin: PluginInfo) {
  const ok = await run(plugin.id, () =>
    apiPlugins.update(plugin.id, { options: drafts.value[plugin.id] })
  );
  if (ok) message.success(t('config.plugins_set.save_success'));
}

onMounted(load);
</script>

<template>
  <ab-fold-panel :title="$t('config.plugins_set.title')">
    <div v-if="overview" class="plugins">
      <AbField
        :label="$t('config.plugins_set.allow_unsigned')"
        :description="$t('config.plugins_set.allow_unsigned_hint')"
      >
        <AbSwitch
          :model-value="overview.allow_unsigned"
          :loading="busy === '__settings'"
          :aria-label="$t('config.plugins_set.allow_unsigned')"
          @update:model-value="setAllowUnsigned"
        />
      </AbField>

      <p v-if="!overview.plugins.length" class="plugins__empty">
        {{ $t('config.plugins_set.empty') }}
      </p>

      <section
        v-for="plugin in overview.plugins"
        :key="plugin.id"
        class="plugin"
      >
        <header class="plugin__header">
          <div class="plugin__title">
            <strong>{{ plugin.name }}</strong>
            <span class="plugin__meta"
              >{{ plugin.id }} · v{{ plugin.version }}</span
            >
          </div>
          <AbSwitch
            :model-value="plugin.enabled"
            :loading="busy === plugin.id"
            :aria-label="$t('config.plugins_set.enabled')"
            @update:model-value="setEnabled(plugin, $event)"
          />
        </header>

        <div class="plugin__tags">
          <AbTag :type="stateType[plugin.state]">
            {{ $t(`config.plugins_set.state_${plugin.state}`) }}
          </AbTag>
          <AbTag>{{ $t(`config.plugins_set.source_${plugin.source}`) }}</AbTag>
          <AbTag v-if="!plugin.signed" type="warning">
            {{ $t('config.plugins_set.unsigned') }}
          </AbTag>
        </div>

        <p v-if="plugin.description" class="plugin__desc">
          {{ plugin.description }}
        </p>
        <AbAlert
          v-if="plugin.error"
          :type="plugin.state === 'error' ? 'danger' : 'info'"
        >
          {{ plugin.error }}
        </AbAlert>
        <p v-if="plugin.permissions.length" class="plugin__desc">
          {{
            $t('config.plugins_set.permissions', {
              list: plugin.permissions.join(', '),
            })
          }}
        </p>

        <details class="plugin__options">
          <summary>{{ $t('config.plugins_set.options') }}</summary>
          <template v-if="plugin.config_schema">
            <PluginSchemaForm
              v-model="drafts[plugin.id]"
              :fields="schemaFields(plugin.config_schema)"
            />
            <AbButton
              size="sm"
              variant="primary"
              class="plugin__save"
              :loading="busy === plugin.id"
              @click="saveOptions(plugin)"
            >
              {{ $t('config.plugins_set.save') }}
            </AbButton>
          </template>
          <p v-else-if="plugin.state === 'active'" class="plugin__desc">
            {{ $t('config.plugins_set.no_options') }}
          </p>
          <p v-else class="plugin__desc">
            {{ $t('config.plugins_set.options_unavailable') }}
          </p>
        </details>
      </section>
    </div>
  </ab-fold-panel>
</template>

<style lang="scss" scoped>
.plugins {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.plugins__empty,
.plugin__desc,
.plugin__meta {
  color: var(--color-text-secondary);
  font-size: 12px;
}

.plugin {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.plugin__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.plugin__title {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.plugin__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.plugin__options summary {
  cursor: pointer;
  font-size: 13px;
  margin-bottom: 8px;
}

.plugin__save {
  margin-top: 12px;
}
</style>
