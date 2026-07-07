/**
 * Contract tests for apiLog: call the real functions against a mocked
 * axios instance so a drift between the wrapper and the FastAPI routes in
 * backend/src/module/api/log.py fails a test instead of going unnoticed.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { mockApiSuccess } from '@/test/mocks/api';
import { createAxiosMock } from '@/test/mocks/axios';

import { apiLog } from '@/api/log';
import { axios } from '@/utils/axios';

vi.mock('@/utils/axios', () => ({ axios: createAxiosMock() }));

describe('Log API contract (path + HTTP method)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should GET api/v1/log when fetching the log', async () => {
    (axios.get as any).mockResolvedValue({ data: 'log contents' });
    await apiLog.getLog();
    expect(axios.get).toHaveBeenCalledWith('api/v1/log', { silent: true });
  });

  it('should POST api/v1/log/clear when clearing the log', async () => {
    (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
    await apiLog.clearLog();
    expect(axios.post).toHaveBeenCalledWith('api/v1/log/clear');
  });
});
