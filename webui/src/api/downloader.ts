import type { DownloaderInstances, QbTorrentInfo } from '#/downloader';
import type { ApiSuccess } from '#/api';

export const apiDownloader = {
  async getTorrents() {
    const { data } = await axios.get<QbTorrentInfo[]>(
      'api/v1/downloader/torrents',
      { silent: true }
    );
    return data!;
  },

  async instances() {
    const { data } = await axios.get<DownloaderInstances>(
      'api/v1/downloader/instances'
    );
    return data!;
  },

  async pause(hashes: string[], downloaderId: string) {
    const { data } = await axios.post<ApiSuccess>(
      'api/v1/downloader/torrents/pause',
      { hashes, downloader_id: downloaderId }
    );
    return data!;
  },

  async resume(hashes: string[], downloaderId: string) {
    const { data } = await axios.post<ApiSuccess>(
      'api/v1/downloader/torrents/resume',
      { hashes, downloader_id: downloaderId }
    );
    return data!;
  },

  async deleteTorrents(
    hashes: string[],
    downloaderId: string,
    deleteFiles = false
  ) {
    const { data } = await axios.post<ApiSuccess>(
      'api/v1/downloader/torrents/delete',
      { hashes, downloader_id: downloaderId, delete_files: deleteFiles }
    );
    return data!;
  },
};
