/**
 * Tests for useMyI18n: a slow locale import must not override a later switch.
 */
import { ref } from 'vue';
import { flushPromises } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

const gate = vi.hoisted(() => {
  let release!: () => void;
  const promise = new Promise<void>((r) => (release = r));
  return { promise, release };
});
// setup.ts 把 createI18n 置空，这里换成带 locale ref 的最小实现
vi.mock('vue-i18n', () => ({
  createI18n: () => ({
    global: { locale: ref('en'), setLocaleMessage: vi.fn(), t: vi.fn() },
  }),
}));
vi.mock('@/i18n/zh-CN.json', async () => {
  await gate.promise;
  return { default: {} };
});

describe('useMyI18n', () => {
  it('should keep the latest locale when an earlier import resolves late', async () => {
    const { useMyI18n } = await import('@/hooks/useMyI18n');
    const { lang, locale } = useMyI18n();
    lang.value = 'zh-CN';
    await flushPromises();
    lang.value = 'en';
    await flushPromises();
    expect(locale.value).toBe('en');

    gate.release();
    await new Promise((r) => setTimeout(r, 50));
    expect(locale.value).toBe('en');
  });
});
