export const apiNotification = {
  async get() {
    const { data } = await axios.get('api/v1/notification');
    return data;
  },

  async getById({ message_id }: { message_id: String }) {
    const { data } = await axios.get('api/v1/notification/get', {
      params: {
        message_id,
      },
    });
    return data;
  },

  async send({ content }: { content: String }) {
    const { data } = await axios.post('api/v1/notification/send', {
      content,
    });

    return data;
  },

  async read({ message_id }: { message_id: String }) {
    const { data } = await axios.get('api/v1/notification/read', {
      params: {
        message_id,
      },
    });
    return data;
  },

  async cleanAllRead() {
    const { data } = await axios.get('api/v1/notification/clean');
    return data;
  },
};
