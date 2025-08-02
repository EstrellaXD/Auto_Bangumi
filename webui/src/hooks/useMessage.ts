import { createDiscreteApi } from 'naive-ui';
import { createSharedComposable } from '@vueuse/core';

export const useMessage = createSharedComposable(() => {
  const { message } = createDiscreteApi(['message']);
  return message;
});
