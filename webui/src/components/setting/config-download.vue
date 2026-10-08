<script lang="ts" setup>
import { Delete, Info, Plus } from '@icon-park/vue-next';
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
const canAdd = computed(
  () =>
    /^[\w-]+$/.test(newId.value) &&
    !plugins.value.instances.some((i) => i.id === newId.value)
);

function addInstance() {
  if (!canAdd.value) return;
  plugins.value.instances.push({
    id: newId.value,
    point: 'downloader',
    provider: 'qbittorrent',
    options: {
      host: '',
      username: '',
      password: '',
      path: '/downloads/Bangumi',
      ssl: false,
    },
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
const pluginProviders = usePluginProviders();
// 插件提供的下载器 id 追加在内置选项之后
const downloaderType = computed(() => [
  ...builtinTypes,
  ...pluginProviders.value.downloader,
]);

const items = computed<SettingItem<DownloaderOptions>[]>(() => [
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
          <span class="instance-meta"
            >{{ i.provider }} · {{ i.options.host }}</span
          >
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
          <ab-button
            size="sm"
            variant="ghost"
            data-action="delete"
            :aria-label="$t('config.downloader_set.delete')"
            @click="removeInstance(i.id)"
          >
            <Delete size="16" />
          </ab-button>
        </template>
      </div>
      <div class="instance-add" data-new-instance>
        <ab-input
          v-model="newId"
          :placeholder="$t('config.downloader_set.new_id')"
          :aria-label="$t('config.downloader_set.new_id')"
          @keyup.enter="addInstance"
        />
        <ab-button
          size="sm"
          data-action="add"
          :disabled="!canAdd"
          @click="addInstance"
        >
          <Plus size="16" />
          {{ $t('config.downloader_set.add') }}
        </ab-button>
      </div>
    </div>

    <div v-if="downloader" space-y-8>
      <div v-if="downloader.provider === 'aria2'" class="downloader-hint">
        <Info size="16" />
        <span>{{ $t('config.downloader_set.aria2_hint') }}</span>
      </div>

      <ab-setting
        v-model:data="downloader.provider"
        :label="() => t('config.downloader_set.type')"
        type="select"
        css="w-115"
        :prop="{ items: downloaderType }"
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
  border-left: 2px solid transparent;

  &.is-editing {
    background: var(--color-surface-2);
    border-left-color: var(--color-primary);
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
  gap: 8px;
  margin-top: 4px;
}

.downloader-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-primary) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-primary) 25%, transparent);
  color: var(--color-text-secondary);
  font-size: 12px;
  transition: background-color var(--transition-normal),
    border-color var(--transition-normal);
}
</style>
