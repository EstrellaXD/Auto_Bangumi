<script lang="ts" setup>
import AbAlert from '../basic/ab-alert.vue';
import AbButton from '../basic/ab-button.vue';
import AbTag from '../basic/ab-tag.vue';
import type { CatalogEntry } from '#/plugins';
import { idLabel } from '@/utils/id-label';
import { permissionDiff, sourceUrl } from '@/utils/plugin-market';

// 安装/更新前的确认步骤，替换详情栏的内容（手机上是同一页的下一步）。
// 更新时 installedPermissions 为已安装版本声明的权限；权限变多须勾选确认。
const props = defineProps<{
  entry: CatalogEntry;
  installedPermissions: string[];
  busy: boolean;
}>();

defineEmits<{ back: []; confirm: [] }>();

const { t } = useMyI18n();

const isUpdate = computed(() => props.entry.installed_version !== null);
const diff = computed(() =>
  isUpdate.value
    ? permissionDiff(props.installedPermissions, props.entry.permissions)
    : { kept: props.entry.permissions, added: [], removed: [] }
);
const acknowledged = ref(false);
const blocked = computed(
  () => diff.value.added.length > 0 && !acknowledged.value
);

function permissionLabel(id: string) {
  return idLabel(t, 'config.plugins_set.permission_labels', id);
}
</script>

<template>
  <section class="confirm">
    <header class="confirm__head">
      <h2 class="confirm__title">
        {{
          $t(isUpdate ? 'market.confirm_update' : 'market.confirm_install', {
            name: entry.name || entry.id,
          })
        }}
      </h2>
      <span class="confirm__version">
        <template v-if="isUpdate"
          >{{ entry.installed_version }} → {{ entry.version }}</template
        >
        <template v-else>{{ entry.version }}</template>
      </span>
    </header>

    <dl class="confirm__kv">
      <template v-if="entry.repo && entry.commit">
        <dt>{{ $t('market.source') }}</dt>
        <dd>
          <a
            class="confirm__link"
            :href="sourceUrl(entry)"
            target="_blank"
            rel="noopener noreferrer"
            >{{ entry.repo }}@{{ entry.commit.slice(0, 7) }}
            <span aria-hidden="true">↗</span></a
          >
        </dd>
        <dt>{{ $t('market.review') }}</dt>
        <dd>{{ $t('market.reviewed') }}</dd>
      </template>

      <dt>{{ $t('market.permissions') }}</dt>
      <dd class="confirm__tags">
        <!-- ab-tag 的 title 是文字内容，原始 id 的提示放在外层 -->
        <span v-for="id in diff.kept" :key="id" :title="id">
          <AbTag>{{ permissionLabel(id) }}</AbTag>
        </span>
        <span
          v-for="id in diff.added"
          :key="`+${id}`"
          class="perm--added"
          :title="`${id} · ${$t('market.permission_added')}`"
        >
          <AbTag type="warning">+ {{ permissionLabel(id) }}</AbTag>
        </span>
        <span
          v-for="id in diff.removed"
          :key="`-${id}`"
          class="perm--removed"
          :title="`${id} · ${$t('market.permission_removed')}`"
        >
          <AbTag>{{ permissionLabel(id) }}</AbTag>
        </span>
        <span
          v-if="!entry.permissions.length && !diff.removed.length"
          class="confirm__muted"
        >
          {{ $t('market.none') }}
        </span>
      </dd>

      <dt>{{ $t('market.frontend') }}</dt>
      <dd>{{ entry.has_web ? $t('market.yes') : $t('market.no') }}</dd>
    </dl>

    <AbAlert type="warning" :title="$t('market.warning_lead')">
      {{ $t('market.warning') }}
    </AbAlert>

    <label v-if="diff.added.length" class="confirm__ack">
      <input v-model="acknowledged" type="checkbox" />
      <span>{{ $t('market.ack_permissions') }}</span>
    </label>

    <footer class="confirm__actions">
      <AbButton variant="ghost" :disabled="busy" @click="$emit('back')">
        {{ $t('market.back') }}
      </AbButton>
      <AbButton
        variant="primary"
        :loading="busy"
        :disabled="blocked"
        @click="$emit('confirm')"
      >
        {{ isUpdate ? $t('market.update') : $t('market.install_enable') }}
      </AbButton>
    </footer>
  </section>
</template>

<style lang="scss" scoped>
.confirm {
  display: flex;
  flex-direction: column;
  gap: 14px;

  // 手机上确认是整屏的一步：撑满详情区，按钮落在底部
  @include forMobile {
    flex-grow: 1;
  }
}

.confirm__head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.confirm__title {
  margin: 0;
  font-size: 17px;
  font-weight: 650;
}

.confirm__version {
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.confirm__kv {
  display: grid;
  grid-template-columns: minmax(64px, max-content) 1fr;
  gap: 8px 14px;
  margin: 0;
  font-size: 13px;

  dt {
    color: var(--color-text-secondary);
  }

  dd {
    min-width: 0;
    margin: 0;
  }
}

.confirm__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.confirm__muted {
  color: var(--color-text-secondary);
}

.confirm__link {
  color: var(--color-text);
  font-family: var(--font-mono);
  font-size: 12px;
  text-decoration: underline;
  text-decoration-color: var(--color-text-muted);
  text-underline-offset: 3px;
  overflow-wrap: anywhere;

  &:hover {
    text-decoration-color: currentColor;
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }
}

.perm--added :deep(.ab-tag) {
  font-weight: 600;
}

.perm--removed :deep(.ab-tag-text) {
  text-decoration: line-through;
}

.confirm__ack {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: var(--touch-target);
  font-size: 13px;
  cursor: pointer;

  input {
    width: 16px;
    height: 16px;
    margin: 0;
    accent-color: var(--color-primary);
    cursor: pointer;
  }
}

// 内容超出时按钮贴在滚动区底部；手机上始终在屏幕底部（底部导航之上）
.confirm__actions {
  position: sticky;
  bottom: 0;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 10px 0;
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);

  @include forMobile {
    margin-top: auto;
    background: var(--color-bg);
  }
}
</style>
