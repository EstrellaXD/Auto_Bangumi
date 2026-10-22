<script lang="ts" setup>
const { title = 'title', flush = false } = defineProps<{
  title: string;
  /** 去掉 body 内边距（内容自带布局时，如列表/表格贴边） */
  flush?: boolean;
}>();
</script>

<template>
  <div class="container-card">
    <div class="container-header">
      <div class="container-title">
        {{ title }}
      </div>
      <slot name="title-right" />
    </div>

    <div class="container-body" :class="{ 'container-body--flush': flush }">
      <slot />
    </div>

    <div v-if="$slots.footer" class="container-footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.container-card {
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  transition: border-color var(--transition-normal);

  // 正文/页脚的方角底色会盖住圆角描边：最后一块跟着卡片圆角。
  // 不用 overflow: hidden，否则卡片边缘的焦点环和定位元素会被裁掉
  > :last-child {
    border-radius: 0 0 calc(var(--radius-md) - 1px) calc(var(--radius-md) - 1px);
  }
}

.container-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  min-height: 34px;
  background: transparent;
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border);
  user-select: none;
  transition: color var(--transition-normal),
    border-color var(--transition-normal);

  // 触屏按钮 44px 高，上下留白，不贴住头部边框
  @include forTouch {
    padding-block: 6px;
  }
}

.container-title {
  font-size: 15px;
  font-weight: 600;
  // 卡片标题不应比正文更浅（层级倒挂），用主文本色，靠字重区分
  color: var(--color-text);
}

.container-body {
  padding: 12px 14px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 14px;
  transition: background-color var(--transition-normal),
    color var(--transition-normal);

  &--flush {
    padding: 0;
  }
}

.container-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 10px 14px;
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}
</style>
