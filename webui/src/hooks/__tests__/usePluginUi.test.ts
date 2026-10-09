/**
 * Tests for usePluginUi: a failed slot request is reported and can be retried.
 */
import { flushPromises } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

import { apiPlugins } from '@/api/plugins';
import {
  refreshPluginUi,
  usePluginPages,
  usePluginUi,
} from '@/hooks/usePluginUi';

vi.mock('@/api/plugins', () => ({
  apiPlugins: { ui: vi.fn() },
}));

describe('usePluginUi', () => {
  it('should set loadFailed when the request fails and clear it on a successful retry', async () => {
    const ui = vi.mocked(apiPlugins.ui);
    ui.mockRejectedValueOnce(new Error('offline'));
    const { loaded, loadFailed } = usePluginUi();
    await flushPromises();
    expect(loadFailed.value).toBe(true);
    expect(loaded.value).toBe(false);

    ui.mockResolvedValueOnce([]);
    await refreshPluginUi();
    expect(loadFailed.value).toBe(false);
    expect(loaded.value).toBe(true);
  });

  // 同一插件的多个页面共用 /plugins/<id> 路由，导航里只出现一项（取第一个页面）
  it('should list one page entry per plugin', async () => {
    const page = (plugin_id: string, element: string) => ({
      plugin_id,
      slot: 'page',
      element,
      entry: 'web/index.js',
      title: { 'en-US': element },
    });
    vi.mocked(apiPlugins.ui).mockResolvedValueOnce([
      page('a', 'a-one'),
      page('a', 'a-two'),
      page('b', 'b-one'),
    ] as never);
    await refreshPluginUi();
    expect(usePluginPages().value.map((ui) => ui.element)).toEqual([
      'a-one',
      'b-one',
    ]);
  });
});
