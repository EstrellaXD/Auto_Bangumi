/**
 * Contract tests for apiPlugins against backend/src/module/api/plugins.py.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createAxiosMock } from '@/test/mocks/axios';

import { apiPlugins } from '@/api/plugins';
import { axios } from '@/utils/axios';

vi.mock('@/utils/axios', () => ({ axios: createAxiosMock() }));

const overview = { allow_unsigned: false, plugins: [] };

describe('Plugins API contract (path + HTTP method)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should GET api/v1/plugins when listing', async () => {
    (axios.get as any).mockResolvedValue({ data: overview });
    expect(await apiPlugins.list()).toEqual(overview);
    expect(axios.get).toHaveBeenCalledWith('api/v1/plugins');
  });

  it('should GET api/v1/plugins/ui when listing UI slots', async () => {
    (axios.get as any).mockResolvedValue({ data: [] });
    expect(await apiPlugins.ui()).toEqual([]);
    expect(axios.get).toHaveBeenCalledWith('api/v1/plugins/ui');
  });

  it('should PUT api/v1/plugins/:id with an encoded id', async () => {
    (axios.put as any).mockResolvedValue({ data: overview });
    await apiPlugins.update('my plugin', { enabled: true });
    expect(axios.put).toHaveBeenCalledWith('api/v1/plugins/my%20plugin', {
      enabled: true,
    });
  });

  it('should PUT api/v1/plugins/settings with allow_unsigned', async () => {
    (axios.put as any).mockResolvedValue({ data: overview });
    await apiPlugins.updateSettings(true);
    expect(axios.put).toHaveBeenCalledWith('api/v1/plugins/settings', {
      allow_unsigned: true,
    });
  });

  it('should GET api/v1/plugins/providers', async () => {
    (axios.get as any).mockResolvedValue({ data: {} });
    await apiPlugins.providers();
    expect(axios.get).toHaveBeenCalledWith('api/v1/plugins/providers');
  });
});
