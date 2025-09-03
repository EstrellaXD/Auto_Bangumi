<script lang="ts" setup>
const show = defineModel('show', {
  default: false,
});

const { t } = useMyI18n();
const message = useMessage();

// 更新信息状态
const updateInfo = ref<{
  current_version: string;
  latest_version: string;
  has_update: boolean;
  release_info: {
    name: string;
    html_url: string;
    published_at: string;
    prerelease: boolean;
    download_url: string;
  };
} | null>(null);

const includePrerelease = ref(false);
const showConfirm = ref(false);

// 使用useApi创建API调用
const { execute: executeCheckUpdate, isLoading: checkingUpdate } = useApi(
  apiProgram.checkUpdate,
  {
    showMessage: false,
    onSuccess: (data) => {
      updateInfo.value = data;
    },
    onError: (error) => {
      console.error('检查更新失败:', error);
      message.error(t('notify.update_failed'));
    }
  }
);

const { execute: executeUpdate, isLoading: updating } = useApi(
  apiProgram.update,
  {
    showMessage: true,
    onSuccess: () => {
      showConfirm.value = false;
      show.value = false;
    },
    onError: (error) => {
      console.error('更新失败:', error);
    }
  }
);

// 检查更新
async function checkUpdate() {
  await executeCheckUpdate(includePrerelease.value);
}

// 执行更新
async function performUpdate() {
  if (!updateInfo.value?.release_info.download_url) {
    message.error(t('notify.update_failed'));
    return;
  }
  await executeUpdate(updateInfo.value.release_info.download_url);
}

// 确认更新
function confirmUpdate() {
  showConfirm.value = true;
}

// 取消更新确认
function cancelUpdate() {
  showConfirm.value = false;
}

// 监听弹窗显示状态，自动检查更新
watch(show, (val) => {
  if (val) {
    checkUpdate();
  } else {
    updateInfo.value = null;
    showConfirm.value = false;
  }
});

// 监听预发布版本选项变化
watch(includePrerelease, () => {
  if (show.value) {
    checkUpdate();
  }
});
</script>

<template>
  <ab-popup
    v-model:show="show"
    :title="$t('topbar.update.title')"
    css="w-500"
  >
    <!-- 确认更新对话框 -->
    <ab-popup
      v-model:show="showConfirm"
      :title="$t('topbar.update.confirm_title')"
      css="w-400"
      :mask-click="false"
    >
      <div space-y-16>
        <p text-center>
          {{ $t('topbar.update.confirm_message', { version: updateInfo?.latest_version }) }}
        </p>
        <div line></div>
        <div flex="~ justify-end gap-x-8">
          <ab-button size="small" @click="cancelUpdate">
            {{ $t('topbar.update.cancel_btn') }}
          </ab-button>
          <ab-button size="small" type="primary" @click="performUpdate">
            {{ $t('topbar.update.update_btn') }}
          </ab-button>
        </div>
      </div>
    </ab-popup>

    <!-- 主要内容 -->
    <div space-y-20>
      <!-- 预发布版本选项 -->
      <div fx-cer justify-between>
        <span>{{ $t('topbar.update.include_prerelease') }}</span>
        <input 
          v-model="includePrerelease" 
          type="checkbox" 
          :disabled="checkingUpdate"
        />
      </div>

      <div line></div>

      <!-- 检查中状态 -->
      <div v-if="checkingUpdate" text-center py-20>
        <p>{{ $t('topbar.update.checking') }}</p>
      </div>

      <!-- 更新信息 -->
      <div v-else-if="updateInfo" space-y-16>
        <!-- 当前版本 -->
        <ab-label :label="$t('topbar.update.current_version')">
          <div ab-input>{{ updateInfo.current_version }}</div>
        </ab-label>

        <!-- 最新版本 -->
        <ab-label :label="$t('topbar.update.latest_version')">
          <div ab-input>{{ updateInfo.latest_version }}</div>
        </ab-label>


        <div line></div>

        <!-- 操作按钮 -->
        <div flex="~ justify-end gap-x-8">
          <ab-button size="small" @click="show = false">
            {{ $t('topbar.update.cancel_btn') }}
          </ab-button>
          <ab-button 
            v-if="updateInfo.has_update"
            size="small" 
            type="primary" 
            @click="confirmUpdate"
          >
            {{ $t('topbar.update.update_btn') }}
          </ab-button>
        </div>
      </div>
    </div>
  </ab-popup>
</template>