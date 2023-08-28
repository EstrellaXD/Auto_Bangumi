export const apiSearch = {
  async get(keyword: string, site = 'mikan') {
    const { data } = await axios.get('api/v1/search', {
      params: {
        site,
        keyword,
      },
    });
    return data!;
  },
};
