import type { QbTorrentInfo } from '#/downloader';
import type { ApiSuccess } from '#/api';

export const apiDownloader = {
  async getTorrents() {
    const { data } = await axios.get<QbTorrentInfo[]>(
      'api/v1/downloader/torrents'
    );
    return data!;
  },

  async pause(hashes: string[]) {
    const { data } = await axios.post<ApiSuccess>(
      'api/v1/downloader/torrents/pause',
      { hashes }
    );
    return data!;
  },

  async resume(hashes: string[]) {
    const { data } = await axios.post<ApiSuccess>(
      'api/v1/downloader/torrents/resume',
      { hashes }
    );
    return data!;
  },

  async deleteTorrents(hashes: string[], deleteFiles: boolean = false) {
    const { data } = await axios.post<ApiSuccess>(
      'api/v1/downloader/torrents/delete',
      { hashes, delete_files: deleteFiles }
    );
    return data!;
  },
};
