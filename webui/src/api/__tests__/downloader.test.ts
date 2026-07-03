/**
 * Contract tests for apiDownloader: call the real functions against a
 * mocked axios instance so a drift between the wrapper and the FastAPI
 * routes in backend/src/module/api/downloader.py fails a test instead of
 * going unnoticed.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { mockApiSuccess, mockTorrents } from '@/test/mocks/api';
import { createAxiosMock } from '@/test/mocks/axios';

import { apiDownloader } from '@/api/downloader';
import { axios } from '@/utils/axios';

vi.mock('@/utils/axios', () => ({ axios: createAxiosMock() }));

describe('Downloader API contract (path + HTTP method)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should GET api/v1/downloader/torrents when fetching torrents', async () => {
    (axios.get as any).mockResolvedValue({ data: mockTorrents });
    await apiDownloader.getTorrents();
    expect(axios.get).toHaveBeenCalledWith('api/v1/downloader/torrents', {
      silent: true,
    });
  });

  it('should POST api/v1/downloader/torrents/pause with hashes when pausing', async () => {
    (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
    await apiDownloader.pause(['abc123', 'def456']);
    expect(axios.post).toHaveBeenCalledWith(
      'api/v1/downloader/torrents/pause',
      {
        hashes: ['abc123', 'def456'],
      }
    );
  });

  it('should POST api/v1/downloader/torrents/resume with hashes when resuming', async () => {
    (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
    await apiDownloader.resume(['abc123']);
    expect(axios.post).toHaveBeenCalledWith(
      'api/v1/downloader/torrents/resume',
      {
        hashes: ['abc123'],
      }
    );
  });

  it('should POST api/v1/downloader/torrents/delete with hashes and delete_files when deleting', async () => {
    (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
    await apiDownloader.deleteTorrents(['abc123'], true);
    expect(axios.post).toHaveBeenCalledWith(
      'api/v1/downloader/torrents/delete',
      {
        hashes: ['abc123'],
        delete_files: true,
      }
    );
  });

  it('should default delete_files to false when deleting without the flag', async () => {
    (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
    await apiDownloader.deleteTorrents(['abc123']);
    expect(axios.post).toHaveBeenCalledWith(
      'api/v1/downloader/torrents/delete',
      {
        hashes: ['abc123'],
        delete_files: false,
      }
    );
  });
});
