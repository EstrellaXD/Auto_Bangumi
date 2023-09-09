<script lang="ts" setup>
import { useMessage } from 'naive-ui';
import type { BangumiRule } from '#/bangumi';
import type { RSS } from '#/rss';
import { rssTemplate } from '#/rss';
import { ruleTemplate } from '#/bangumi';
import type { ApiError } from "#/api";

/** v-model show */
const show = defineModel('show', { default: false });

const message = useMessage();
const { getAll } = useBangumiStore();

const rss = ref<RSS>(rssTemplate);
const searchRule = defineModel<BangumiRule>('searchRule', { default: null });
const rule = ref<BangumiRule>(ruleTemplate);
const parserType = ['mikan', 'tmdb', 'parser'];

const window = reactive({
  loading: false,
  rule: false,
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
      window.next = false;
    }, 300);
  } else if (val || searchRule.value)  {
    window.next = true;
    window.rule = true;
    rule.value = searchRule.value;
  }
});

async function addRss() {
  if (rss.value.url === '') {
    message.error('Please enter the RSS link!');
  } else if (rss.value.aggregate) {
    try {
      window.loading = true;
      const data = await apiRSS.add(rss.value);
      window.loading = false;
      window.next = true;
      message.success(data.msg_en);
      show.value = false;
      console.log('rss', data);
    } catch (error) {
      const err = error as ApiError;
      message.error(err.msg_en);
      console.log('error', err.msg_en);
      window.loading = false;
    }
  } else {
    try {
      window.loading = true;
      const data = await apiDownload.analysis(rss.value);
      window.loading = false;
      rule.value = data;
      window.next = true;
      window.rule = true;
      console.log('rule', data);
    } catch (error) {
      const err = error as ApiError;
      message.error(err.msg_en);
      console.log('error', err.msg_en);
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
    <div v-if="!window.next" space-y-12px>
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
          :loading="window.loading"
          @click="addRss"
          >{{ $t('topbar.add.button') }}</ab-button
        >
      </div>
    </div>

    <div v-else-if="window.rule">
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
