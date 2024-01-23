import type { NotificationResponse } from '#/notification';

export const apiNotification = {
  async getTotal() {
    const { data } = await axios.get<NotificationResponse>(
      'api/v1/notification/total'
    );
    return data;
  },

  async get({ page, limit }: { page?: number; limit?: number }) {
    const { data } = await axios.get<NotificationResponse>(
      'api/v1/notification',
      {
        params: {
          page,
          limit,
        },
      }
    );
    return data;
  },

  async getById({ message_id }: { message_id: string }) {
    const { data } = await axios.get<NotificationResponse>(
      'api/v1/notification/get',
      {
        params: {
          message_id,
        },
      }
    );
    return data;
  },

  async send({ content }: { content: string }) {
    const { data } = await axios.post<NotificationResponse>(
      'api/v1/notification/send',
      {
        content,
      }
    );

    return data;
  },

  async setRead({ message_ids }: { message_ids: string[] }) {
    const { data } = await axios.post<NotificationResponse>(
      'api/v1/notification/read',
      {
        message_ids,
      }
    );
    return data;
  },

  async cleanAll() {
    const { data } = await axios.get<NotificationResponse>(
      'api/v1/notification/clean'
    );
    return data;
  },
};
