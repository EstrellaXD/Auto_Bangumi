<script lang="ts" setup>
import { useMessage } from 'naive-ui';
import type { BangumiRule } from '#/bangumi';

const { getAll } = useBangumiStore();
const show = defineModel('show', { default: false });

const rss = ref('');
const message = useMessage();
const rule = ref<BangumiRule>({
  added: false,
  deleted: false,
  dpi: '',
  eps_collect: false,
  filter: [],
  group_name: '',
  id: 0,
  official_title: '',
  offset: 0,
  poster_link: '',
  rss_link: [],
  rule_name: '',
  save_path: '',
  season: 1,
  season_raw: '',
  source: null,
  subtitle: '',
  title_raw: '',
  year: null,
});
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

async function analyser() {
  if (rss.value === '') {
    message.error('Please enter the RSS link!');
  } else {
    try {
      analysis.loading = true;
      const { onError, onResult } = await apiDownload.analysis(rss.value);
      onResult((data) => {
        rule.value = data;
        analysis.loading = false;
        analysis.next = true;
        console.log('rule', data);
      });

      onError((err) => {
        message.error(err.status);
        analysis.loading = false;
        console.log('error', err);
      });
    } catch (error) {
      message.error('Failed to analyser!');
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
  <ab-popup v-model:show="show" title="Add Bangumi" css="w-360px">
    <div v-if="!analysis.next" space-y-12px>
      <ab-setting
        v-model:data="rss"
        label="RSS Link"
        type="input"
        :prop="{
          placeholder: 'Please enter the RSS link',
        }"
        :bottom-line="true"
      ></ab-setting>

      <div flex="~ justify-end">
        <ab-button size="small" :loading="analysis.loading" @click="analyser"
          >Analyse</ab-button
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
