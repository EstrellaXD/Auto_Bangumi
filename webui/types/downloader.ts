export type QbTorrentState =
  | 'error'
  | 'missingFiles'
  | 'uploading'
  | 'pausedUP'
  | 'queuedUP'
  | 'stalledUP'
  | 'checkingUP'
  | 'forcedUP'
  | 'allocating'
  | 'downloading'
  | 'metaDL'
  | 'pausedDL'
  | 'queuedDL'
  | 'stalledDL'
  | 'checkingDL'
  | 'forcedDL'
  | 'checkingResumeData'
  | 'moving'
  | 'unknown';

export interface QbTorrentInfo {
  hash: string;
  name: string;
  size: number;
  progress: number;
  dlspeed: number;
  upspeed: number;
  num_seeds: number;
  num_leechs: number;
  state: QbTorrentState;
  eta: number;
  category: string;
  save_path: string;
  added_on: number;
  /** 种子所在的下载器实例 id */
  downloader_id: string;
}

/** 下载器实例列表（GET /downloader/instances） */
export interface DownloaderInstances {
  /** 默认实例 id（plugins.slots.downloader） */
  default: string;
  instances: { id: string; provider: string }[];
}

export interface TorrentGroup {
  name: string;
  savePath: string;
  totalSize: number;
  overallProgress: number;
  count: number;
  torrents: QbTorrentInfo[];
}
