/**
 * Contract tests for apiSearch: call the real functions against a mocked
 * axios instance so a drift between the wrapper and the FastAPI routes in
 * backend/src/module/api/search.py fails a test instead of going
 * unnoticed.
 *
 * Note: `apiSearch.get()` is an EventSource-based composable, not an axios
 * call, so it is out of scope for this contract test.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createAxiosMock } from '@/test/mocks/axios';

import { apiSearch } from '@/api/search';
import { axios } from '@/utils/axios';

vi.mock('@/utils/axios', () => ({ axios: createAxiosMock() }));

describe('Search API contract (path + HTTP method)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should GET api/v1/search/provider when fetching providers', async () => {
    (axios.get as any).mockResolvedValue({ data: ['mikan', 'dmhy'] });
    await apiSearch.getProvider();
    expect(axios.get).toHaveBeenCalledWith('api/v1/search/provider');
  });
});
