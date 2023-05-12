<script lang="ts" setup>
import {
  form,
  rssParserLang,
  rssParserType,
  rssParserMethodType,
  tfOptions,
} from '../form-data';

const rssParser = computed(() => form.rss_parser);

const filter = ref('');
watch(filter, (nv) => {
  const value = nv.split(',').filter((e) => e !== '');
  rssParser.value.filter = value;
});
</script>

<template>
  <ConfigFormRow title="RSS 解析">
    <ConfigFormCol label="启用">
      <el-select v-model="rssParser.enable" flex-1>
        <el-option
          v-for="(opt, index) in tfOptions"
          :key="index"
          :label="opt.label"
          :value="opt.value"
        ></el-option>
      </el-select>
    </ConfigFormCol>

    <ConfigFormCol label="源">
      <el-select v-model="rssParser.type" flex-1>
        <el-option
          v-for="opt in rssParserType"
          :key="opt"
          :value="opt"
        ></el-option>
      </el-select>
    </ConfigFormCol>

    <ConfigFormCol label="token">
      <el-input v-model="rssParser.token"></el-input>
    </ConfigFormCol>

    <ConfigFormCol label="语言">
      <el-select v-model="rssParser.language" flex-1>
        <el-option
          v-for="opt in rssParserLang"
          :key="opt"
          :value="opt"
        ></el-option>
      </el-select>
    </ConfigFormCol>

    <ConfigFormCol label="源站链接">
      <el-input v-model="rssParser.custom_url"></el-input>
    </ConfigFormCol>

    <ConfigFormCol label="解析类型">
      <el-select v-model="rssParser.parser_type" flex-1>
        <el-option
          v-for="(opt, index) in rssParserMethodType"
          :key="opt"
          :value="opt"
        ></el-option>
      </el-select>
    </ConfigFormCol>

    <ConfigFormCol label="筛选">
      <el-input v-model="filter" :value="rssParser.filter.join(',')"></el-input>
    </ConfigFormCol>
  </ConfigFormRow>
</template>
