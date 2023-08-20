<script lang="ts" setup>
import { useMessage } from 'naive-ui';
import type { BangumiRule } from '#/bangumi';
import { ruleTemplate } from '#/bangumi';

/** v-model show */
const show = defineModel('show', { default: false });

const message = useMessage();
const { getAll } = useBangumiStore();

const rss = ref('');
const rule = ref<BangumiRule>(ruleTemplate);

const analysis = reactive({
  loading: false,
  next: false,
});
const loading = reactive({
  collect: false,
  subscribe: false,
});

watch(show, (val) => {
  if (!val) {
    rss.value = '';
    setTimeout(() => {
      analysis.next = false;
    }, 300);
  }
});

async function analysisRss() {
  if (rss.value === '') {
    message.error('Please enter the RSS link!');
  } else {
    try {
      analysis.loading = true;
      const data = await apiDownload.analysis(rss.value);
      analysis.loading = false;

      rule.value = data;
      analysis.next = true;
      console.log('rule', data);
    } catch (error) {
      const err = error as { status: string };
      message.error(err.status);
      console.log('error', err);
    }
  }
}

async function collect() {
  if (rule.value) {
    try {
      loading.collect = true;
      const res = await apiDownload.collection(rule.value);
      loading.collect = false;

      if (res) {
        message.success('Collect Success!');
        getAll();
        show.value = false;
      } else {
        message.error('Collect Failed!');
      }
    } catch (error) {
      message.error('Collect Error!');
    }
  }
}

async function subscribe() {
  if (rule.value) {
    try {
      loading.subscribe = true;
      const res = await apiDownload.subscribe(rule.value);
      loading.subscribe = false;
      if (res) {
        message.success('Subscribe Success!');
        getAll();
        show.value = false;
      } else {
        message.error('Subscribe Failed!');
      }
    } catch (error) {
      message.error('Subscribe Error!');
    }
  }
}
</script>

<template>
  <ab-popup v-model:show="show" :title="$t('topbar.add.title')" css="w-360px">
    <div v-if="!analysis.next" space-y-12px>
      <ab-setting
        v-model:data="rss"
        :label="$t('topbar.add.rss_link')"
        type="input"
        :prop="{
          placeholder: $t('topbar.add.placeholder_link'),
        }"
      ></ab-setting>
      <ab-setting
        v-model:data="rule"
        :label="$t('topbar.add.name')"
        type="input"
        :prop="{
          placeholder: $t('topbar.add.placeholder_name'),
        }"
      ></ab-setting>
      <ab-setting
        v-model:data="rule"
        :label="$t('topbar.add.aggregate')"
        type="switch"
      ></ab-setting>
      <ab-setting
        v-model:data="rule"
        :label="$t('topbar.add.parser')"
        type="select"
        :bottom-line="true"
      ></ab-setting>

      <div flex="~ justify-end">
        <ab-button
          size="small"
          :loading="analysis.loading"
          @click="analysisRss"
          >{{ $t('topbar.add.analyse') }}</ab-button
        >
      </div>
    </div>

    <div v-else>
      <ab-rule v-model:rule="rule"></ab-rule>

      <div flex="~ justify-end" space-x-10px>
        <ab-button size="small" :loading="loading.collect" @click="collect"
          >Collect</ab-button
        >
        <ab-button size="small" :loading="loading.subscribe" @click="subscribe"
          >Subscribe</ab-button
        >
      </div>
    </div>
  </ab-popup>
</template>
