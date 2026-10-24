/**
 * #1145：路由守卫在 app.runWithContext() 中第一次调用 useAuth() → useMessage()。
 * 此时创建的 discrete app 会从外层应用查找 n-message-provider，message 为 undefined，
 * 登录成功后 message.success 抛错，跳转不执行。
 */
import { describe, expect, it } from 'vitest';
import { createApp } from 'vue';
import { useMessage } from '@/hooks/useMessage';

describe('useMessage', () => {
  it('should return a working message API when first called inside app.runWithContext', () => {
    const app = createApp({});

    const message = app.runWithContext(() => useMessage());

    expect(typeof message?.success).toBe('function');
  });
});
