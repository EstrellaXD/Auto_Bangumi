/**
 * Contract tests for apiSetup: call the real functions against a mocked
 * axios instance so a drift between the wrapper and the FastAPI routes in
 * backend/src/module/api/setup.py fails a test instead of going unnoticed.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { mockApiSuccess } from '@/test/mocks/api';
import { createAxiosMock } from '@/test/mocks/axios';
import type {
  SetupCompleteRequest,
  TestDownloaderRequest,
  TestNotificationRequest,
} from '#/setup';

import { apiSetup } from '@/api/setup';
import { axios } from '@/utils/axios';

vi.mock('@/utils/axios', () => ({ axios: createAxiosMock() }));

const mockTestResult = {
  success: true,
  message_en: 'ok',
  message_zh: '成功',
};

describe('Setup API contract (path + HTTP method)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should GET api/v1/setup/status when fetching setup status', async () => {
    (axios.get as any).mockResolvedValue({
      data: { need_setup: true, version: 'DEV_VERSION' },
    });
    await apiSetup.getStatus();
    expect(axios.get).toHaveBeenCalledWith('api/v1/setup/status');
  });

  it('should POST api/v1/setup/test-downloader with the config when testing the downloader', async () => {
    (axios.post as any).mockResolvedValue({ data: mockTestResult });
    const config: TestDownloaderRequest = {
      type: 'qbittorrent',
      host: '172.17.0.1:8080',
      username: 'admin',
      password: 'adminadmin',
      ssl: false,
    };
    await apiSetup.testDownloader(config);
    expect(axios.post).toHaveBeenCalledWith('api/v1/setup/test-downloader', config);
  });

  it('should POST api/v1/setup/test-rss with the url when testing an RSS feed', async () => {
    (axios.post as any).mockResolvedValue({ data: mockTestResult });
    await apiSetup.testRSS('https://mikanani.me/RSS/MyBangumi');
    expect(axios.post).toHaveBeenCalledWith('api/v1/setup/test-rss', {
      url: 'https://mikanani.me/RSS/MyBangumi',
    });
  });

  it('should POST api/v1/setup/test-notification with the config when testing a notification provider', async () => {
    (axios.post as any).mockResolvedValue({ data: mockTestResult });
    const config: TestNotificationRequest = {
      type: 'telegram',
      token: 'abc',
      chat_id: '123',
    };
    await apiSetup.testNotification(config);
    expect(axios.post).toHaveBeenCalledWith(
      'api/v1/setup/test-notification',
      config
    );
  });

  it('should POST api/v1/setup/complete with the wizard config when completing setup', async () => {
    (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
    const config: SetupCompleteRequest = {
      username: 'admin',
      password: 'adminadmin',
      downloader_type: 'qbittorrent',
      downloader_host: '172.17.0.1:8080',
      downloader_username: 'admin',
      downloader_password: 'adminadmin',
      downloader_path: '/downloads/Bangumi',
      downloader_ssl: false,
      rss_url: '',
      rss_name: '',
      notification_enable: false,
      notification_type: 'telegram',
      notification_token: '',
      notification_chat_id: '',
    };
    await apiSetup.complete(config);
    expect(axios.post).toHaveBeenCalledWith('api/v1/setup/complete', config);
  });
});
