<script lang="ts" setup>
import { useMessage } from 'naive-ui';
import type { BangumiRule } from '#/bangumi';
import type { RSS } from '#/rss';
import { rssTemplate } from '#/rss';
import { ruleTemplate } from '#/bangumi';
import { registerSW } from 'virtual:pwa-register';

/** v-model show */
const show = defineModel('show', { default: false });

const message = useMessage();
const { getAll } = useBangumiStore();

const rss = ref<RSS>(rssTemplate);
const rule = ref<BangumiRule>(ruleTemplate);

const parserType = ['mikan', 'tmdb', 'parser'];

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
    rss.value = rssTemplate;
    setTimeout(() => {
      analysis.next = false;
    }, 300);
  }
});

async function addRss() {
  if (rss.value.url === '') {
    message.error('Please enter the RSS link!');
  } else if (rss.value.aggregate) {
    try {
      analysis.loading = true;
      const data = await apiRSS.add(rss.value);
      analysis.loading = false;
      analysis.next = true;
      if (data.status) {
        message.success(data.msg_en);
        show.value = false;
        console.log('rss', data);
      } else {
        message.error(data.msg_en);
      }
      // TODO 这部分 WebUI 无法判断 406 错误无法跳出信息。
      // RSS API 添加正常。后端正常。
    } catch (error) {
      const err = error as { status: string };
      message.error(err.status);
      console.log('error', err);
    }
  } else {
    try {
      analysis.loading = true;
      const data = await apiDownload.analysis(rss.value.url);
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
        v-model:data="rss.url"
        :label="$t('topbar.add.rss_link')"
        type="input"
        :prop="{
          placeholder: $t('topbar.add.placeholder_link'),
        }"
      ></ab-setting>
      <ab-setting
        v-model:data="rss.name"
        :label="$t('topbar.add.name')"
        type="input"
        :prop="{
          placeholder: $t('topbar.add.placeholder_name'),
        }"
      ></ab-setting>
      <ab-setting
        v-model:data="rss.aggregate"
        :label="$t('topbar.add.aggregate')"
        type="switch"
      ></ab-setting>
      <ab-setting
        v-model:data="rss.parser"
        :label="$t('topbar.add.parser')"
        type="select"
        :prop="{
          items: parserType,
        }"
        :bottom-line="true"
      ></ab-setting>

      <div flex="~ justify-end">
        <ab-button
          size="small"
          :loading="analysis.loading"
          @click="addRss"
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
