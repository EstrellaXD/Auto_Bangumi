/**
 * Contract tests for apiUpdate: call the real functions against a mocked axios
 * instance so a drift between the wrapper and the FastAPI routes in
 * backend/src/module/api/update.py fails a test instead of going unnoticed.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createAxiosMock } from '@/test/mocks/axios';

import { apiUpdate } from '@/api/update';
import { axios } from '@/utils/axios';

vi.mock('@/utils/axios', () => ({ axios: createAxiosMock() }));

const mockInfo = {
  current: '3.2.0',
  latest: '3.3.0',
  has_update: true,
  channel: 'stable',
  notes: 'notes',
  published_at: null,
  is_prerelease: false,
  bundle_url: 'https://example/bundle.zip',
  sha256_url: 'https://example/bundle.zip.sha256',
  applied_version: null,
  can_rollback: false,
  error: null,
};

const mockApply = {
  success: true,
  message: 'ok',
  version: '3.3.0',
  restart_required: true,
};

describe('Update API contract (path + HTTP method)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should GET api/v1/update/check with the channel param when checking', async () => {
    (axios.get as any).mockResolvedValue({ data: mockInfo });
    await apiUpdate.check('beta');
    expect(axios.get).toHaveBeenCalledWith('api/v1/update/check', {
      params: { channel: 'beta' },
    });
  });

  it('should GET api/v1/update/check without params when channel omitted', async () => {
    (axios.get as any).mockResolvedValue({ data: mockInfo });
    await apiUpdate.check();
    expect(axios.get).toHaveBeenCalledWith('api/v1/update/check', {
      params: undefined,
    });
  });

  it('should POST api/v1/update/apply with the channel param when applying', async () => {
    (axios.post as any).mockResolvedValue({ data: mockApply });
    await apiUpdate.apply('stable');
    expect(axios.post).toHaveBeenCalledWith('api/v1/update/apply', null, {
      params: { channel: 'stable' },
    });
  });

  it('should POST api/v1/update/rollback when rolling back', async () => {
    (axios.post as any).mockResolvedValue({ data: mockApply });
    await apiUpdate.rollback();
    expect(axios.post).toHaveBeenCalledWith('api/v1/update/rollback');
  });
});
