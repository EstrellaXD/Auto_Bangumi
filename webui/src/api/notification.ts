import type { NotificationProviderConfig, NotificationType } from '#/config';
import type { TupleToUnion } from '#/utils';

export interface TestProviderRequest {
  provider_index: number;
}

export interface TestProviderConfigRequest {
  type: TupleToUnion<NotificationType>;
  enabled?: boolean;
  token?: string;
  chat_id?: string;
  webhook_url?: string;
  server_url?: string;
  device_key?: string;
  user_key?: string;
  api_token?: string;
  template?: string;
  url?: string;
}

export interface TestResponse {
  success: boolean;
  message: string;
  message_zh: string;
  message_en: string;
}

export const apiNotification = {
  /**
   * Test a configured provider by index
   */
  async testProvider(request: TestProviderRequest) {
    const { data } = await axios.post<TestResponse>(
      'api/v1/notification/test',
      request
    );
    return { data };
  },

  /**
   * Test an unsaved provider configuration
   */
  async testProviderConfig(request: TestProviderConfigRequest) {
    const { data } = await axios.post<TestResponse>(
      'api/v1/notification/test-config',
      request
    );
    return { data };
  },
};
