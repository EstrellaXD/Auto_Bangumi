/**
 * Contract tests for apiConfig: call the real functions against a mocked
 * axios instance so a drift between the wrapper and the FastAPI routes in
 * backend/src/module/api/config.py fails a test instead of going unnoticed.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { mockApiSuccess, mockConfig } from '@/test/mocks/api';
import { createAxiosMock } from '@/test/mocks/axios';
import type { Config } from '#/config';

import { apiConfig } from '@/api/config';
import { axios } from '@/utils/axios';

vi.mock('@/utils/axios', () => ({ axios: createAxiosMock() }));

describe('Config API contract (path + HTTP method)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should GET api/v1/config/get when fetching config', async () => {
    (axios.get as any).mockResolvedValue({ data: mockConfig });
    await apiConfig.getConfig();
    expect(axios.get).toHaveBeenCalledWith('api/v1/config/get');
  });

  it('should PATCH api/v1/config/update with the config payload when updating', async () => {
    (axios.patch as any).mockResolvedValue({ data: mockApiSuccess });
    await apiConfig.updateConfig(mockConfig as unknown as Config);
    expect(axios.patch).toHaveBeenCalledWith('api/v1/config/update', mockConfig);
  });
});
