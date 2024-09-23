import { createDiscreteApi } from 'naive-ui';

export const useMessage = createSharedComposable(() => {
  const { message } = createDiscreteApi(['message']);
  return message;
});
