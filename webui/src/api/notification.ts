import type { NotificationType } from '#/config';
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

export type InboxSeverity = 'info' | 'warning' | 'error';

export interface InboxMessage {
  id: number;
  kind: string;
  severity: InboxSeverity;
  title: string;
  body: string;
  payload: Record<string, string | number> | null;
  read: boolean;
  count: number;
  created_at: string;
  updated_at: string;
}

export interface InboxListResponse {
  messages: InboxMessage[];
  total: number;
  unread_count: number;
}

export interface InboxListParams {
  unread_only?: boolean;
  limit?: number;
  offset?: number;
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

  /** 收件箱：分页列表（后台刷新，静默失败） */
  async getMessages(params: InboxListParams = {}) {
    const { data } = await axios.get<InboxListResponse>(
      'api/v1/notification/messages',
      { params, silent: true }
    );
    return data!;
  },

  /** 收件箱：未读数（SSE 断开时的轮询回退） */
  async getUnreadCount() {
    const { data } = await axios.get<{ unread_count: number }>(
      'api/v1/notification/messages/unread-count',
      { silent: true }
    );
    return data!.unread_count;
  },

  async markRead(id: number) {
    await axios.post(`api/v1/notification/messages/${id}/read`);
  },

  async markAllRead() {
    await axios.post('api/v1/notification/messages/read-all');
  },

  async removeMessage(id: number) {
    await axios.delete(`api/v1/notification/messages/${id}`);
  },

  async clearAll() {
    await axios.delete('api/v1/notification/messages');
  },
};
