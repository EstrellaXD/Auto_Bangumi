<script lang="ts" setup>
import AbAlert from '../basic/ab-alert.vue';
import AbButton from '../basic/ab-button.vue';
import AbField from '../basic/ab-field.vue';
import AbSkeleton from '../basic/ab-skeleton.vue';
import AbSwitch from '../basic/ab-switch.vue';
import AbTag from '../basic/ab-tag.vue';
import PluginSchemaForm from './plugin-schema-form.vue';
import type { CatalogEntry, PluginInfo, PluginsOverview } from '#/plugins';
import { apiPlugins } from '@/api/plugins';
import { useConfirm } from '@/hooks/useConfirm';
import { refreshPluginProviders } from '@/hooks/usePluginProviders';
import { refreshPluginUi } from '@/hooks/usePluginUi';
import { fillSchemaDefaults, schemaFields } from '@/utils/plugin-schema';

// 插件卡片不参与全局保存：每次改动直接调 /plugins 接口落盘并应用，
// 随后刷新 config store 的 plugins 段，避免全局保存用旧值覆盖。
const { t } = useMyI18n();
const message = useMessage();
const { confirm } = useConfirm();
const { refreshGroup } = useConfigStore();

const overview = ref<PluginsOverview | null>(null);
const drafts = ref<Record<string, Record<string, unknown>>>({});
const busy = ref<string | null>(null);

// 签名目录要访问 GitHub，用户点「浏览目录」时才拉取；
// catalogError 为 '' 表示失败但后端没给出原因
const catalog = ref<CatalogEntry[] | null>(null);
const catalogLoading = ref(false);
const catalogError = ref<string | null>(null);

const stateType = {
  active: 'success',
  disabled: 'neutral',
  error: 'danger',
} as const;

// 只重建服务端配置或 schema 有变化的插件草稿，其它卡片里未保存的编辑保留
function apply(data: PluginsOverview) {
  const saved = (p?: PluginInfo) =>
    p && JSON.stringify([p.options, p.config_schema]);
  const prev = new Map(overview.value?.plugins.map((p) => [p.id, p]));
  overview.value = data;
  drafts.value = Object.fromEntries(
    data.plugins.map((p) => [
      p.id,
      drafts.value[p.id] && saved(prev.get(p.id)) === saved(p)
        ? drafts.value[p.id]
        : fillSchemaDefaults(schemaFields(p.config_schema), p.options),
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

async function run(
  key: string,
  action: () => Promise<PluginsOverview>,
  failKey = 'save_failed'
) {
  busy.value = key;
  try {
    apply(await action());
    // 只刷新插件卡片保存的字段，保留未保存的下载器实例与 slots 修改
    await refreshGroup('plugins', ['allow_unsigned', 'enabled', 'options']);
    // 插件启停会增减下载器/通知渠道候选，同步刷新下拉框
    await refreshPluginProviders();
    // 启停也会增减插件的前端挂载点
    await refreshPluginUi();
    return true;
  } catch {
    // 后端的具体原因（如验签失败）由 axios 拦截器另行提示
    message.error(t(`config.plugins_set.${failKey}`));
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

async function loadCatalog() {
  catalogLoading.value = true;
  catalogError.value = null;
  try {
    catalog.value = await apiPlugins.catalog();
  } catch (e) {
    const detail = (e as { response?: { data?: { detail?: unknown } } })
      .response?.data?.detail;
    catalogError.value = typeof detail === 'string' ? detail : '';
  } finally {
    catalogLoading.value = false;
  }
}

async function install(entry: CatalogEntry) {
  const ok = await run(
    `install:${entry.id}`,
    () => apiPlugins.install(entry.id),
    'install_failed'
  );
  if (!ok) return;
  entry.installed_version = entry.version;
  message.success(t('config.plugins_set.install_success'));
}

// 只有签名目录安装的插件（source 为 catalog）显示卸载按钮：后端卸载的前提
// （installed.json 指向含 plugin.toml 的版本目录）与加载器判定 catalog 来源
// 是同一条件。LLM 提供商插件不在此列表中，仍在 LLM 设置里管理。
async function uninstall(plugin: PluginInfo) {
  const confirmed = await confirm({
    title: t('config.plugins_set.uninstall_confirm_title', {
      name: plugin.name,
    }),
    body: t('config.plugins_set.uninstall_confirm_body'),
    confirmText: t('config.plugins_set.uninstall'),
    danger: true,
  });
  if (!confirmed) return;
  const ok = await run(
    `uninstall:${plugin.id}`,
    () => apiPlugins.uninstall(plugin.id),
    'uninstall_failed'
  );
  if (!ok) return;
  const entry = catalog.value?.find((e) => e.id === plugin.id);
  if (entry) entry.installed_version = null;
  message.success(t('config.plugins_set.uninstall_success'));
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
          <AbTag v-if="plugin.signed" type="success">
            {{ $t('config.plugins_set.signed') }}
          </AbTag>
          <AbTag v-else type="warning">
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

        <AbButton
          v-if="plugin.source === 'catalog'"
          size="sm"
          variant="danger"
          class="plugin__uninstall"
          :loading="busy === `uninstall:${plugin.id}`"
          @click="uninstall(plugin)"
        >
          {{ $t('config.plugins_set.uninstall') }}
        </AbButton>
      </section>

      <section class="catalog">
        <header class="plugin__header">
          <div class="plugin__title">
            <strong>{{ $t('config.plugins_set.catalog_title') }}</strong>
            <span class="plugin__desc">
              {{ $t('config.plugins_set.catalog_hint') }}
            </span>
          </div>
          <AbButton size="sm" :loading="catalogLoading" @click="loadCatalog">
            {{
              catalog
                ? $t('config.plugins_set.catalog_refresh')
                : $t('config.plugins_set.catalog_browse')
            }}
          </AbButton>
        </header>

        <AbAlert
          v-if="catalogError !== null"
          type="danger"
          :title="$t('config.plugins_set.catalog_failed')"
        >
          {{ catalogError || $t('config.plugins_set.catalog_failed_hint') }}
        </AbAlert>
        <AbSkeleton v-else-if="catalogLoading && !catalog" preset="row" />
        <p v-else-if="catalog && !catalog.length" class="plugins__empty">
          {{ $t('config.plugins_set.catalog_empty') }}
        </p>

        <ul v-if="catalog?.length" class="catalog__list">
          <li v-for="entry in catalog" :key="entry.id" class="catalog__entry">
            <div class="plugin__title">
              <strong>{{ entry.name || entry.id }}</strong>
              <span class="plugin__meta"
                >{{ entry.id }} · v{{ entry.version }}</span
              >
              <span v-if="entry.description" class="plugin__desc">
                {{ entry.description }}
              </span>
              <span v-if="entry.extension_points.length" class="plugin__desc">
                {{
                  $t('config.plugins_set.extension_points', {
                    list: entry.extension_points.join(', '),
                  })
                }}
              </span>
            </div>
            <span
              v-if="entry.installed_version === entry.version"
              class="plugin__desc"
            >
              {{ $t('config.plugins_set.installed') }}
            </span>
            <div v-else class="catalog__action">
              <span v-if="entry.installed_version" class="plugin__desc">
                {{
                  $t('config.plugins_set.installed_version', {
                    version: entry.installed_version,
                  })
                }}
              </span>
              <AbButton
                size="sm"
                variant="primary"
                :loading="busy === `install:${entry.id}`"
                @click="install(entry)"
              >
                {{
                  entry.installed_version
                    ? $t('config.plugins_set.update')
                    : $t('config.plugins_set.install')
                }}
              </AbButton>
            </div>
          </li>
        </ul>
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

.plugin__uninstall {
  align-self: flex-start;
}

.plugin__meta {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.catalog {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
}

.catalog__list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.catalog__entry {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border-radius: var(--radius-md);
  background: var(--color-surface-2);
}

.catalog__action {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 8px;
}
</style>
