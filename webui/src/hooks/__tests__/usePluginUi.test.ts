/**
 * Tests for usePluginUi: a failed slot request is reported and can be retried.
 */
import { flushPromises } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

import { apiPlugins } from '@/api/plugins';
import { refreshPluginUi, usePluginUi } from '@/hooks/usePluginUi';

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
});
