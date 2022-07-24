<script setup lang="ts">
import ShowResults from '@/components/ShowResults.vue';
import { addBangumi } from '@/api/bangumi';

const props = defineProps<{
  type: string
}>()

const rssLink = ref();
const loading = ref(false);
const dialog = ref();
const dialogData = ref(null);

const add = async () => {
  loading.value = true;
  const res = await addBangumi(props.type, rssLink.value);
  if (res){
    loading.value = false;
    dialogData.value = res.data;
    dialog.value.open();
  }
}

</script>

<template>
  <ShowResults
    ref="dialog"
    title="执行结果"
    :results="dialogData"
  />

  <el-card shadow="hover">
    <template #header>
      <div class="card-header">
        <span v-if="type === 'new'">订阅新番</span>
        <span v-else-if="type === 'old'">订阅旧番</span>
      </div>
    </template>

    <div class="card-con">
      <el-input
        v-model="rssLink"
        placeholder="请输入番剧的rss链接"
      >
        <template #append>
          <el-button
            type="primary"
            :loading="loading"
            @click="add"
          >订阅</el-button>
        </template>
      </el-input>
    </div>

  </el-card>
</template>