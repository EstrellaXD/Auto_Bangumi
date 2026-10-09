/**
 * Tests for usePluginProviders: plugin provider ids follow plugin enable/disable.
 */
import { describe, expect, it, vi } from 'vitest';

import { apiPlugins } from '@/api/plugins';
import {
  refreshPluginProviders,
  usePluginProviders,
} from '@/hooks/usePluginProviders';

vi.mock('@/api/plugins', () => ({
  apiPlugins: { providers: vi.fn() },
}));

const empty = {
  downloader: [],
  notifier: [],
  search_site: [],
  metadata_provider: [],
  rename_strategy: [],
};

describe('usePluginProviders', () => {
  it('should refetch provider ids when refreshPluginProviders is called', async () => {
    const providers = vi.mocked(apiPlugins.providers);
    providers.mockResolvedValueOnce(empty);
    const ids = usePluginProviders();
    expect(providers).toHaveBeenCalledTimes(1);

    providers.mockResolvedValueOnce({ ...empty, downloader: ['ext-dl'] });
    await refreshPluginProviders();
    expect(ids.value.downloader).toEqual(['ext-dl']);
  });
});
