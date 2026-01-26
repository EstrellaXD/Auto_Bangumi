<script lang="ts" setup>
import { Delete, EditTwo, Plus } from '@icon-park/vue-next';

interface SearchProvider {
  name: string;
  url: string;
}

const { t } = useMyI18n();

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

// Default providers that cannot be deleted
const defaultProviderNames = ['mikan', 'nyaa', 'dmhy'];

onMounted(() => {
  loadProviders();
});

async function loadProviders() {
  loading.value = true;
  try {
    const response = await fetch('/api/v1/search/provider/config');
    if (response.ok) {
      const data = await response.json();
      providers.value = Object.entries(data).map(([name, url]) => ({
        name,
        url: url as string,
      }));
    }
  } catch (error) {
    console.error('Failed to load providers:', error);
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
    const response = await fetch('/api/v1/search/provider/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(providerObj),
    });
    if (!response.ok) {
      throw new Error('Failed to save providers');
    }
  } catch (error) {
    console.error('Failed to save providers:', error);
  }
}

function openAddDialog() {
  formName.value = '';
  formUrl.value = '';
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
  if (!formName.value.trim() || !formUrl.value.trim()) return;

  // Check for duplicate name
  if (providers.value.some((p) => p.name === formName.value.trim())) {
    return;
  }

  providers.value.push({
    name: formName.value.trim(),
    url: formUrl.value.trim(),
  });

  await saveProviders();
  showAddDialog.value = false;
  formName.value = '';
  formUrl.value = '';
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

  if (!confirm(t('config.search_provider_set.delete_confirm'))) return;

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
              <span v-if="isDefaultProvider(provider.name)" class="default-badge">
                {{ $t('config.search_provider_set.default') }}
              </span>
            </div>
            <div class="provider-url" :title="provider.url">
              {{ provider.url }}
            </div>
          </div>
          <div class="provider-actions">
            <ab-button
              size="small"
              type="secondary"
              @click="openEditDialog(provider, index)"
            >
              <EditTwo size="16" />
            </ab-button>
            <ab-button
              v-if="!isDefaultProvider(provider.name)"
              size="small"
              type="warn"
              @click="handleDelete(index)"
            >
              <Delete size="16" />
            </ab-button>
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
        <ab-button size="small" type="primary" @click="openAddDialog">
          <Plus size="16" />
          {{ $t('config.search_provider_set.add_new') }}
        </ab-button>
      </div>
    </div>

    <!-- Add dialog -->
    <ab-popup
      v-model:show="showAddDialog"
      :title="$t('config.search_provider_set.add_title')"
      css="w-400"
    >
      <div space-y-16>
        <ab-label :label="$t('config.search_provider_set.name')">
          <input
            v-model="formName"
            type="text"
            :placeholder="$t('config.search_provider_set.name_placeholder')"
            ab-input
            maxlength="32"
          />
        </ab-label>

        <ab-label :label="$t('config.search_provider_set.url')">
          <input
            v-model="formUrl"
            type="text"
            :placeholder="$t('config.search_provider_set.url_placeholder')"
            ab-input
            @keyup.enter="handleAdd"
          />
        </ab-label>

        <div
          v-if="formUrl && !validateUrl(formUrl)"
          class="validation-warning"
        >
          {{ $t('config.search_provider_set.url_missing_placeholder') }}
        </div>

        <div line></div>

        <div flex="~ justify-end gap-8">
          <ab-button size="small" type="warn" @click="showAddDialog = false">
            {{ $t('config.cancel') }}
          </ab-button>
          <ab-button
            size="small"
            type="primary"
            :disabled="!formName.trim() || !formUrl.trim() || !validateUrl(formUrl)"
            @click="handleAdd"
          >
            {{ $t('config.apply') }}
          </ab-button>
        </div>
      </div>
    </ab-popup>

    <!-- Edit dialog -->
    <ab-popup
      v-model:show="showEditDialog"
      :title="$t('config.search_provider_set.edit_title')"
      css="w-400"
    >
      <div space-y-16>
        <ab-label :label="$t('config.search_provider_set.name')">
          <input
            v-model="formName"
            type="text"
            :placeholder="$t('config.search_provider_set.name_placeholder')"
            ab-input
            maxlength="32"
            :disabled="editingProvider !== null && isDefaultProvider(editingProvider.name)"
          />
        </ab-label>

        <ab-label :label="$t('config.search_provider_set.url')">
          <input
            v-model="formUrl"
            type="text"
            :placeholder="$t('config.search_provider_set.url_placeholder')"
            ab-input
            @keyup.enter="handleEdit"
          />
        </ab-label>

        <div
          v-if="formUrl && !validateUrl(formUrl)"
          class="validation-warning"
        >
          {{ $t('config.search_provider_set.url_missing_placeholder') }}
        </div>

        <div line></div>

        <div flex="~ justify-end gap-8">
          <ab-button size="small" type="warn" @click="showEditDialog = false">
            {{ $t('config.cancel') }}
          </ab-button>
          <ab-button
            size="small"
            type="primary"
            :disabled="!formName.trim() || !formUrl.trim() || !validateUrl(formUrl)"
            @click="handleEdit"
          >
            {{ $t('config.apply') }}
          </ab-button>
        </div>
      </div>
    </ab-popup>
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
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
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

.validation-warning {
  font-size: 12px;
  color: var(--color-danger, #ef4444);
  padding: 8px 12px;
  background: color-mix(in srgb, var(--color-danger, #ef4444) 10%, transparent);
  border-radius: 6px;
}
</style>
