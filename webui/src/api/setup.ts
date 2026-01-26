import type {
  SetupCompleteRequest,
  SetupStatus,
  TestDownloaderRequest,
  TestNotificationRequest,
  TestResult,
} from '#/setup';
import type { ApiSuccess } from '#/api';

export const apiSetup = {
  async getStatus() {
    const { data } = await axios.get<SetupStatus>('api/v1/setup/status');
    return data;
  },

  async testDownloader(config: TestDownloaderRequest) {
    const { data } = await axios.post<TestResult>(
      'api/v1/setup/test-downloader',
      config
    );
    return data;
  },

  async testRSS(url: string) {
    const { data } = await axios.post<TestResult>('api/v1/setup/test-rss', {
      url,
    });
    return data;
  },

  async testNotification(config: TestNotificationRequest) {
    const { data } = await axios.post<TestResult>(
      'api/v1/setup/test-notification',
      config
    );
    return data;
  },

  async complete(config: SetupCompleteRequest) {
    const { data } = await axios.post<ApiSuccess>(
      'api/v1/setup/complete',
      config
    );
    return data;
  },
};
