<script setup lang="ts">
defineProps<{
  title: string;
  results: object | null;
}>();

const dialogVisible = ref(false);
function handleClose() {
  dialogVisible.value = false;
}
function open() {
  dialogVisible.value = true;
}

defineExpose({
  open,
});
</script>

<template>
  <div class="dia-log">
    <el-dialog
      v-model="dialogVisible"
      :title="title"
      width="30%"
      :before-close="handleClose"
    >
      <div>
        <div class="results">
          {{ results === null ? 'null' : results }}
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style lang="scss" scope>
.dia-log {
  .results {
    padding: 1em;
    line-height: 1.5;
    color: #fff;
    background: #333;
  }
}
</style>
