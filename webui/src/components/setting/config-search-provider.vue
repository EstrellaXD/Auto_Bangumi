<script lang="ts" setup>
import { Delete, EditTwo, Plus } from '@icon-park/vue-next';
import { useConfirm } from '@/hooks/useConfirm';
import {
  buildNexusPhpSearchUrl,
  isValidNexusPhpCategoryIds,
} from '@/utils/nexusphp';

interface SearchProvider {
  name: string;
  url: string;
}

const { t } = useMyI18n();
const { confirm } = useConfirm();

async function onDeleteClick(index: number) {
  const ok = await confirm({
    title: t('config.search_provider_set.remove'),
    body: t('config.search_provider_set.delete_confirm'),
    confirmText: t('config.search_provider_set.remove'),
    danger: true,
  });
  if (ok) handleDelete(index);
}
const message = useMessage();

// State
const providers = ref<SearchProvider[]>([]);
const loading = ref(false);
const showAddDialog = ref(false);
const showEditDialog = ref(false);
const editingProvider = ref<SearchProvider | null>(null);
const editingIndex = ref<number>(-1);

// Form state
const formName = ref('');
const formUrl = ref('');

// Add-dialog mode: custom URL template, or NexusPHP PT-site preset that
// builds a torrentrss.php search template from base URL + passkey.
type AddMode = 'custom' | 'nexusphp';
const formMode = ref<AddMode>('custom');
const formBaseUrl = ref('');
const formPasskey = ref('');
const formCategoryId = ref('');

const addModeOptions = computed(() => [
  { label: t('config.search_provider_set.mode_custom'), value: 'custom' },
  { label: t('config.search_provider_set.mode_nexusphp'), value: 'nexusphp' },
]);

const categoryIdsValid = computed(() =>
  isValidNexusPhpCategoryIds(formCategoryId.value)
);

const builtNexusPhpUrl = computed(() => {
  if (!formBaseUrl.value.trim() || !formPasskey.value.trim()) return '';
  if (!categoryIdsValid.value) return '';
  return buildNexusPhpSearchUrl({
    baseUrl: formBaseUrl.value,
    passkey: formPasskey.value,
    categoryId: formCategoryId.value,
  });
});

// 预览里遮住 passkey（存储的 URL 不变——供应商列表本就显示完整 URL）
const previewNexusPhpUrl = computed(() =>
  builtNexusPhpUrl.value.replace(
    /(passkey=)([^&]+)/,
    (_, prefix: string, key: string) =>
      `${prefix}${key.length > 4 ? `${key.slice(0, 4)}…` : '…'}`
  )
);

const addFormUrl = computed(() =>
  formMode.value === 'nexusphp' ? builtNexusPhpUrl.value : formUrl.value.trim()
);

const canAdd = computed(
  () =>
    !!formName.value.trim() &&
    !!addFormUrl.value &&
    validateUrl(addFormUrl.value)
);

// Default providers that cannot be deleted
const defaultProviderNames = ['mikan', 'nyaa', 'dmhy'];

onMounted(() => {
  loadProviders();
});

async function loadProviders() {
  loading.value = true;
  try {
    const { data } = await axios.get<Record<string, string>>(
      'api/v1/search/provider/config'
    );
    providers.value = Object.entries(data).map(([name, url]) => ({
      name,
      url,
    }));
  } catch (error) {
    console.error('Failed to load providers:', error);
    message.error(t('config.search_provider_set.load_failed'));
  } finally {
    loading.value = false;
  }
}

async function saveProviders() {
  const providerObj: Record<string, string> = {};
  providers.value.forEach((p) => {
    providerObj[p.name] = p.url;
  });

  try {
    await axios.put('api/v1/search/provider/config', providerObj);
    message.success(t('config.search_provider_set.save_success'));
  } catch (error) {
    console.error('Failed to save providers:', error);
    message.error(t('config.search_provider_set.save_failed'));
  }
}

function openAddDialog() {
  formName.value = '';
  formUrl.value = '';
  formMode.value = 'custom';
  formBaseUrl.value = '';
  formPasskey.value = '';
  formCategoryId.value = '';
  showAddDialog.value = true;
}

function openEditDialog(provider: SearchProvider, index: number) {
  editingProvider.value = provider;
  editingIndex.value = index;
  formName.value = provider.name;
  formUrl.value = provider.url;
  showEditDialog.value = true;
}

async function handleAdd() {
  if (!canAdd.value) return;

  // Check for duplicate name
  if (providers.value.some((p) => p.name === formName.value.trim())) {
    return;
  }

  providers.value.push({
    name: formName.value.trim(),
    url: addFormUrl.value,
  });

  await saveProviders();
  showAddDialog.value = false;
  formName.value = '';
  formUrl.value = '';
  formBaseUrl.value = '';
  formPasskey.value = '';
  formCategoryId.value = '';
}

async function handleEdit() {
  if (!formName.value.trim() || !formUrl.value.trim()) return;
  if (editingIndex.value < 0) return;

  // Check for duplicate name (excluding current)
  const duplicateIndex = providers.value.findIndex(
    (p, i) => p.name === formName.value.trim() && i !== editingIndex.value
  );
  if (duplicateIndex !== -1) return;

  providers.value[editingIndex.value] = {
    name: formName.value.trim(),
    url: formUrl.value.trim(),
  };

  await saveProviders();
  showEditDialog.value = false;
  editingProvider.value = null;
  editingIndex.value = -1;
  formName.value = '';
  formUrl.value = '';
}

async function handleDelete(index: number) {
  const provider = providers.value[index];
  if (defaultProviderNames.includes(provider.name)) {
    return;
  }

  providers.value.splice(index, 1);
  await saveProviders();
}

function isDefaultProvider(name: string): boolean {
  return defaultProviderNames.includes(name);
}

function validateUrl(url: string): boolean {
  return url.includes('%s');
}
</script>

<template>
  <ab-fold-panel :title="$t('config.search_provider_set.title')">
    <div space-y-8>
      <!-- Loading state -->
      <div v-if="loading" text-gray-500 text-14>
        {{ $t('passkey.loading') }}
      </div>

      <!-- Empty state -->
      <div v-else-if="providers.length === 0" text-gray-500 text-14>
        {{ $t('config.search_provider_set.no_providers') }}
      </div>

      <!-- Provider list -->
      <div v-else space-y-8>
        <div
          v-for="(provider, index) in providers"
          :key="provider.name"
          class="provider-item"
        >
          <div class="provider-info">
            <div class="provider-name">
              {{ provider.name }}
              <span
                v-if="isDefaultProvider(provider.name)"
                class="default-badge"
              >
                {{ $t('config.search_provider_set.default') }}
              </span>
            </div>
            <div class="provider-url" :title="provider.url">
              {{ provider.url }}
            </div>
          </div>
          <div class="provider-actions">
            <ab-button
              size="sm"
              variant="secondary"
              @click="openEditDialog(provider, index)"
            >
              <EditTwo size="16" />
            </ab-button>
            <ab-icon-button
              v-if="!isDefaultProvider(provider.name)"
              size="sm"
              class="provider-delete"
              :label="$t('config.search_provider_set.remove')"
              @click="onDeleteClick(index)"
            >
              <Delete size="16" />
            </ab-icon-button>
          </div>
        </div>
      </div>

      <div line></div>

      <!-- Hint text -->
      <div class="hint-text">
        {{ $t('config.search_provider_set.url_hint') }}
      </div>

      <!-- Add button -->
      <div flex="~ justify-end">
        <ab-button size="sm" variant="primary" @click="openAddDialog">
          <Plus size="16" />
          {{ $t('config.search_provider_set.add_new') }}
        </ab-button>
      </div>
    </div>

    <!-- Add dialog -->
    <ab-modal
      v-model:show="showAddDialog"
      size="sm"
      :title="$t('config.search_provider_set.add_title')"
    >
      <div space-y-16>
        <ab-segmented
          v-model:value="formMode"
          size="sm"
          :options="addModeOptions"
          :aria-label="$t('config.search_provider_set.add_title')"
        />

        <ab-field :label="$t('config.search_provider_set.name')">
          <ab-input
            v-model="formName"
            :placeholder="
              formMode === 'nexusphp'
                ? $t('config.search_provider_set.name_placeholder_nexusphp')
                : $t('config.search_provider_set.name_placeholder')
            "
            :maxlength="32"
          />
        </ab-field>

        <template v-if="formMode === 'custom'">
          <ab-field :label="$t('config.search_provider_set.url')">
            <ab-input
              v-model="formUrl"
              type="text"
              :placeholder="$t('config.search_provider_set.url_placeholder')"
              @keyup.enter="handleAdd"
            />
          </ab-field>

          <div
            v-if="formUrl && !validateUrl(formUrl)"
            class="validation-warning"
          >
            {{ $t('config.search_provider_set.url_missing_placeholder') }}
          </div>
        </template>

        <template v-else>
          <ab-field :label="$t('config.search_provider_set.base_url')">
            <ab-input
              v-model="formBaseUrl"
              type="text"
              :placeholder="
                $t('config.search_provider_set.base_url_placeholder')
              "
            />
          </ab-field>

          <ab-field :label="$t('config.search_provider_set.passkey')">
            <ab-input
              v-model="formPasskey"
              type="text"
              :placeholder="
                $t('config.search_provider_set.passkey_placeholder')
              "
            />
          </ab-field>

          <ab-field :label="$t('config.search_provider_set.category_id')">
            <ab-input
              v-model="formCategoryId"
              type="text"
              :placeholder="
                $t('config.search_provider_set.category_id_placeholder')
              "
              @keyup.enter="handleAdd"
            />
          </ab-field>

          <div
            v-if="formCategoryId && !categoryIdsValid"
            class="validation-warning"
          >
            {{ $t('config.search_provider_set.category_id_invalid') }}
          </div>

          <div class="hint-text">
            {{ $t('config.search_provider_set.nexusphp_hint') }}
          </div>

          <div v-if="previewNexusPhpUrl" class="url-preview">
            {{ previewNexusPhpUrl }}
          </div>
        </template>
      </div>

      <template #footer>
        <ab-button size="sm" @click="showAddDialog = false">
          {{ $t('config.cancel') }}
        </ab-button>
        <ab-button
          size="sm"
          variant="primary"
          :disabled="!canAdd"
          @click="handleAdd"
        >
          {{ $t('config.apply') }}
        </ab-button>
      </template>
    </ab-modal>

    <!-- Edit dialog -->
    <ab-modal
      v-model:show="showEditDialog"
      size="sm"
      :title="$t('config.search_provider_set.edit_title')"
    >
      <div space-y-16>
        <ab-field :label="$t('config.search_provider_set.name')">
          <ab-input
            v-model="formName"
            :placeholder="$t('config.search_provider_set.name_placeholder')"
            :maxlength="32"
            :disabled="
              editingProvider !== null &&
              isDefaultProvider(editingProvider.name)
            "
          />
        </ab-field>

        <ab-field :label="$t('config.search_provider_set.url')">
          <ab-input
            v-model="formUrl"
            type="text"
            :placeholder="$t('config.search_provider_set.url_placeholder')"
            @keyup.enter="handleEdit"
          />
        </ab-field>

        <div v-if="formUrl && !validateUrl(formUrl)" class="validation-warning">
          {{ $t('config.search_provider_set.url_missing_placeholder') }}
        </div>
      </div>

      <template #footer>
        <ab-button size="sm" @click="showEditDialog = false">
          {{ $t('config.cancel') }}
        </ab-button>
        <ab-button
          size="sm"
          variant="primary"
          :disabled="
            !formName.trim() || !formUrl.trim() || !validateUrl(formUrl)
          "
          @click="handleEdit"
        >
          {{ $t('config.apply') }}
        </ab-button>
      </template>
    </ab-modal>
  </ab-fold-panel>
</template>

<style lang="scss" scoped>
.provider-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  background: var(--color-surface-elevated, #f9fafb);
  border-radius: 8px;
  transition: background-color var(--transition-normal);

  :root.dark & {
    background: var(--color-surface-elevated, #1f2937);
  }
}

.provider-info {
  flex: 1;
  min-width: 0;
}

.provider-name {
  font-weight: 500;
  font-size: 14px;
  color: var(--color-text);
  display: flex;
  align-items: center;
  gap: 8px;
}

.default-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--color-primary);
  color: white;
  opacity: 0.8;
}

.provider-url {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas,
    monospace;
}

.provider-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.hint-text {
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.url-preview {
  font-size: 12px;
  color: var(--color-text-secondary);
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas,
    monospace;
  padding: 8px 12px;
  background: var(--color-surface-elevated, #f9fafb);
  border-radius: 6px;
  word-break: break-all;

  :root.dark & {
    background: var(--color-surface-elevated, #1f2937);
  }
}

.validation-warning {
  font-size: 12px;
  color: var(--color-danger, #ef4444);
  padding: 8px 12px;
  background: color-mix(in srgb, var(--color-danger, #ef4444) 10%, transparent);
  border-radius: 6px;
}
.provider-delete {
  color: var(--color-danger);

  &:hover:not(:disabled) {
    color: var(--color-danger);
    background: color-mix(in srgb, var(--color-danger) 12%, transparent);
  }
}
</style>
