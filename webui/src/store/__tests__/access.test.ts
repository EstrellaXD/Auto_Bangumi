import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiTokens, apiUsers } from '@/api/access';
import { useAccessStore } from '@/store/access';
import type { ApiTokenCreated } from '#/access';

vi.mock('@/api/access', () => ({
  apiUsers: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
  apiTokens: {
    list: vi.fn(),
    create: vi.fn(),
    revoke: vi.fn(),
  },
}));

const createdToken: ApiTokenCreated = {
  id: 9,
  user_id: 2,
  name: 'automation',
  scope: 'api',
  prefix: 'ab_api_12345',
  created_at: '2026-07-10T08:00:00Z',
  last_used_at: null,
  expires_at: null,
  revoked_at: null,
  token: 'ab_api_one_time_secret',
};

describe('access store', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiUsers.list).mockResolvedValue([]);
    vi.mocked(apiTokens.list).mockRejectedValue(
      new Error('the follow-up list is unavailable')
    );
  });

  it('returns a created token secret without depending on a second list request', async () => {
    vi.mocked(apiTokens.create).mockResolvedValue(createdToken);
    const store = useAccessStore();

    await expect(store.createToken('automation', 'api')).resolves.toBe(
      'ab_api_one_time_secret'
    );

    expect(apiTokens.list).not.toHaveBeenCalled();
    expect(store.tokens).toEqual([
      expect.objectContaining({
        id: 9,
        name: 'automation',
        prefix: 'ab_api_12345',
      }),
    ]);
    expect('token' in store.tokens[0]).toBe(false);
  });
});
