/**
 * Contract tests for apiCheck: call the real functions against a mocked
 * axios instance so a drift between the wrapper and the FastAPI route in
 * backend/src/module/api/program.py (the "check/downloader" endpoint) fails
 * a test instead of going unnoticed.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createAxiosMock } from '@/test/mocks/axios';

import { apiCheck } from '@/api/check';
import { axios } from '@/utils/axios';

vi.mock('@/utils/axios', () => ({ axios: createAxiosMock() }));

describe('Check API contract (path + HTTP method)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should GET api/v1/check/downloader when checking the downloader', async () => {
    (axios.get as any).mockResolvedValue({ data: true });
    await apiCheck.downloader();
    expect(axios.get).toHaveBeenCalledWith('api/v1/check/downloader');
  });
});
