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
}

export interface TorrentGroup {
  name: string;
  savePath: string;
  totalSize: number;
  overallProgress: number;
  count: number;
  torrents: QbTorrentInfo[];
}
