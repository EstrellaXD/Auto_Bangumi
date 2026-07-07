/**
 * Contract tests for apiDownload: call the real functions against a mocked
 * axios instance so a drift between the wrapper and the FastAPI routes in
 * backend/src/module/api/rss.py (the legacy analysis/collect/subscribe
 * endpoints) fails a test instead of going unnoticed.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { mockApiSuccess, mockBangumiAPI, mockBangumiRule, mockRSSItem } from '@/test/mocks/api';
import { createAxiosMock } from '@/test/mocks/axios';

import { apiDownload } from '@/api/download';
import { axios } from '@/utils/axios';

vi.mock('@/utils/axios', () => ({ axios: createAxiosMock() }));

describe('Download API contract (path + HTTP method)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should POST api/v1/rss/analysis with the RSS payload when analysing a link', async () => {
    (axios.post as any).mockResolvedValue({ data: mockBangumiAPI });
    await apiDownload.analysis(mockRSSItem);
    expect(axios.post).toHaveBeenCalledWith('api/v1/rss/analysis', mockRSSItem);
  });

  it('should POST api/v1/rss/collect with the joined filter/rss_link when collecting a season', async () => {
    (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
    await apiDownload.collection(mockBangumiRule);
    expect(axios.post).toHaveBeenCalledWith('api/v1/rss/collect', mockBangumiAPI);
  });

  it('should POST api/v1/rss/subscribe with the bangumi and rss payload when subscribing', async () => {
    (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
    await apiDownload.subscribe(mockBangumiRule, mockRSSItem);
    expect(axios.post).toHaveBeenCalledWith('api/v1/rss/subscribe', {
      data: mockBangumiAPI,
      rss: mockRSSItem,
    });
  });
});
