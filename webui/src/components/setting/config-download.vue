<script lang="ts" setup>
import { Delete, Plus } from '@icon-park/vue-next';
import type { DownloaderOptions, DownloaderType } from '#/config';
import type { SettingItem } from '#/components';
import { useConfirm } from '@/hooks/useConfirm';
import { usePluginProviders } from '@/hooks/usePluginProviders';

const { t } = useMyI18n();
const { confirm } = useConfirm();
const { getSettingGroup } = useConfigStore();

const plugins = getSettingGroup('plugins');
const downloaders = computed(() =>
  plugins.value.instances.filter((i) => i.point === 'downloader')
);
// 正在编辑的实例，默认为默认实例（plugins.slots.downloader）
const editingId = ref(plugins.value.slots.downloader);
const downloader = computed(
  () =>
    downloaders.value.find((i) => i.id === editingId.value) ??
    downloaders.value.find((i) => i.id === plugins.value.slots.downloader)
);

const newId = ref('');
const idValid = computed(() => /^[\w-]+$/.test(newId.value));
const idTaken = computed(() =>
  plugins.value.instances.some((i) => i.id === newId.value)
);
const canAdd = computed(() => idValid.value && !idTaken.value);
// 输入非空且不可用时说明原因
const idError = computed(() => {
  if (!newId.value) return '';
  if (!idValid.value) return t('config.downloader_set.id_invalid');
  return idTaken.value ? t('config.downloader_set.id_taken') : '';
});

// 空白 options；切换下载器类型时重置，避免旧类型的凭据带入新类型
function defaultOptions() {
  return {
    host: '',
    username: '',
    password: '',
    path: '/downloads/Bangumi',
    ssl: false,
  } satisfies DownloaderOptions;
}

function setProvider(provider: string) {
  if (!downloader.value || downloader.value.provider === provider) return;
  downloader.value.provider = provider;
  downloader.value.options = defaultOptions();
}

function addInstance() {
  if (!canAdd.value) return;
  plugins.value.instances.push({
    id: newId.value,
    point: 'downloader',
    provider: 'qbittorrent',
    options: defaultOptions(),
  });
  editingId.value = newId.value;
  newId.value = '';
}

async function removeInstance(id: string) {
  const ok = await confirm({
    title: t('config.downloader_set.delete'),
    body: t('config.downloader_set.delete_confirm', { id }),
    confirmText: t('config.downloader_set.delete'),
    danger: true,
  });
  if (!ok) return;
  plugins.value.instances = plugins.value.instances.filter((i) => i.id !== id);
  if (editingId.value === id) editingId.value = plugins.value.slots.downloader;
}
const builtinTypes: DownloaderType = ['qbittorrent', 'aria2'];
// 内置下载器显示产品名；插件提供的 id 标明来自插件
const builtinLabels: Record<string, string> = {
  qbittorrent: 'qBittorrent',
  aria2: 'aria2',
};
function providerLabel(id: string) {
  return builtinLabels[id] ?? t('config.downloader_set.plugin_label', { id });
}
const pluginProviders = usePluginProviders();
// 插件提供的下载器 id 追加在内置选项之后
const downloaderType = computed(() =>
  [...builtinTypes, ...pluginProviders.value.downloader].map((value, id) => ({
    id,
    value,
    label: providerLabel(value),
  }))
);

const allItems = computed<SettingItem<DownloaderOptions>[]>(() => [
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
]);
// aria2 以 RPC secret 认证，不使用用户名
const items = computed(() =>
  allItems.value.filter(
    (i) =>
      !(downloader.value?.provider === 'aria2' && i.configKey === 'username')
  )
);
</script>

<template>
  <ab-fold-panel :title="$t('config.downloader_set.title')">
    <div class="instance-list">
      <div
        v-for="i in downloaders"
        :key="i.id"
        :data-instance="i.id"
        class="instance-row"
        :class="{ 'is-editing': i.id === downloader?.id }"
      >
        <ab-button
          variant="ghost"
          size="sm"
          class="instance-main"
          :aria-pressed="i.id === downloader?.id"
          @click="editingId = i.id"
        >
          <span class="instance-id">{{ i.id }}</span>
          <span class="instance-meta">{{
            i.options.host
              ? `${providerLabel(i.provider)} · ${i.options.host}`
              : providerLabel(i.provider)
          }}</span>
        </ab-button>
        <span v-if="i.id === plugins.slots.downloader" class="instance-default">
          {{ $t('config.downloader_set.default') }}
        </span>
        <template v-else>
          <ab-button
            size="sm"
            variant="ghost"
            data-action="set-default"
            @click="plugins.slots.downloader = i.id"
          >
            {{ $t('config.downloader_set.set_default') }}
          </ab-button>
          <ab-icon-button
            size="sm"
            data-action="delete"
            :label="$t('config.downloader_set.delete')"
            @click="removeInstance(i.id)"
          >
            <Delete size="16" />
          </ab-icon-button>
        </template>
      </div>
      <div class="instance-add" data-new-instance>
        <ab-field
          class="instance-add-field"
          :label="$t('config.downloader_set.new_id')"
          :description="$t('config.downloader_set.new_id_hint')"
          :error="idError"
        >
          <ab-input v-model="newId" @keyup.enter="addInstance" />
        </ab-field>
        <ab-button data-action="add" :disabled="!canAdd" @click="addInstance">
          <Plus size="16" />
          {{ $t('config.downloader_set.add') }}
        </ab-button>
      </div>
    </div>

    <div v-if="downloader" space-y-8>
      <ab-alert v-if="downloader.provider === 'aria2'">
        {{ $t('config.downloader_set.aria2_hint') }}
      </ab-alert>

      <ab-setting
        :data="downloader.provider"
        :label="() => t('config.downloader_set.type')"
        type="select"
        css="w-115"
        :prop="{ items: downloaderType }"
        @update:data="setProvider"
      ></ab-setting>
      <ab-setting
        v-for="i in items"
        :key="i.configKey"
        v-bind="i"
        v-model:data="downloader.options[i.configKey]"
      ></ab-setting>
    </div>
  </ab-fold-panel>
</template>

<style lang="scss" scoped>
.instance-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 16px;
}

.instance-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);

  &.is-editing {
    background: var(--color-primary-light);
  }
}

.instance-main {
  flex: 1;
  min-width: 0;
  justify-content: flex-start;
  gap: 12px;
  color: var(--color-text);
}

.instance-id {
  font-weight: 500;
}

.instance-meta,
.instance-default {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.instance-add {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 4px;
}

.instance-add-field {
  flex: 1;
}
</style>
