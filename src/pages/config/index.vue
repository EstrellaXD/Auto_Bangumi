<script lang="ts" setup>
import ProgramItem from './components/ProgramItem.vue';
import DownloaderItem from './components/DownloaderItem.vue';
import RssParserItem from './components/RssParserItem.vue';
import BangumiManageItem from './components/BangumiManageItem.vue';
import LogItem from './components/LogItem.vue';
import ProxyItem from './components/ProxyItem.vue';
import NotificationItem from './components/NotificationItem.vue';

import { form } from './form-data';

const store = configStore();

function submit() {
  store.set(form);
}

function formSync() {
  if (store.config) {
    Object.keys(store.config).forEach((key) => {
      if (store.config) {
        form[key] = JSON.parse(JSON.stringify(store.config[key]));
      }
    });
  }
}

onActivated(async () => {
  await store.get();
  formSync();
});
</script>

<template>
  <section class="settings" pb30>
    <el-row :gutter="20">
      <el-col :xs="24" :sm="24">
        <el-form :model="form" label-position="right">
          <el-collapse>
            <ProgramItem />
            <DownloaderItem />
            <RssParserItem />
            <BangumiManageItem />
            <LogItem />
            <ProxyItem />
            <NotificationItem />
          </el-collapse>
        </el-form>
      </el-col>
    </el-row>

    <div flex="~ items-center justify-center" mt20>
      <el-button type="primary" @click="submit">保存</el-button>
      <el-button @click="formSync">还原</el-button>
    </div>
  </section>
</template>

<style lang="scss" scope>
.el-row {
  &:not(:last-child) {
    margin-bottom: 20px;
  }
}
</style>
