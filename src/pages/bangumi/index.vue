<script setup lang="ts">
import BangumiData from './components/BangumiData.vue'
import AddBangumi from './components/AddBangumi.vue'
</script>

<template>
  <section class="bangumi">
    <el-row>
      <!-- S 番剧列表 -->
      <el-col>
        <BangumiData />
      </el-col>
      <!-- E 番剧列表 -->
    </el-row>

    <el-row :gutter="20">

      <!-- S 添加新番 -->
      <el-col :span="8">
        <AddBangumi type="new" />
      </el-col>
      <!-- E 添加新番 -->

      <!-- S 添加旧番 -->
      <el-col :span="8">
        <AddBangumi type="old" />
      </el-col>
      <!-- E 添加旧番 -->

    </el-row>
  </section>
</template>

<style lang='scss' scope>
.el-row {
  &:not(:last-child) {
    margin-bottom: 20px;
  }
}
</style>