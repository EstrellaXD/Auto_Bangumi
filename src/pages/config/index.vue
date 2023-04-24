<script lang="ts" setup></script>

<template>
  <section class="settings">
    <el-row :gutter="20">
      <!-- S 添加新番 -->
      <el-col :xs="24" :sm="24" :md="12" :lg="8">
        <AddBangumi type="new" />
      </el-col>
      <!-- E 添加新番 -->

      <!-- S 添加旧番 -->
      <el-col :xs="24" :sm="24" :md="12" :lg="8">
        <AddBangumi type="old" />
      </el-col>
      <!-- E 添加旧番 -->
    </el-row>
  </section>
</template>

<style lang="scss" scope>
.el-row {
  &:not(:last-child) {
    margin-bottom: 20px;
  }
}
</style>
