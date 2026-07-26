export type TorrentStateType = 'success' | 'danger' | 'info' | 'neutral';

type Translate = (key: string) => string;

const STATE_LABELS: Readonly<Record<string, string>> = {
  downloading: 'downloader.state.downloading',
  uploading: 'downloader.state.seeding',
  pausedDL: 'downloader.state.paused',
  pausedUP: 'downloader.state.paused',
  stoppedDL: 'downloader.state.paused',
  stoppedUP: 'downloader.state.paused',
  stalledDL: 'downloader.state.stalled',
  stalledUP: 'downloader.state.seeding',
  queuedDL: 'downloader.state.queued',
  queuedUP: 'downloader.state.queued',
  checkingDL: 'downloader.state.checking',
  checkingUP: 'downloader.state.checking',
  error: 'downloader.state.error',
  missingFiles: 'downloader.state.error',
  metaDL: 'downloader.state.metadata',
};

export function formatTorrentSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const unitIndex = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / 1024 ** unitIndex).toFixed(1)} ${units[unitIndex]}`;
}

export function formatTorrentSpeed(bytesPerSecond: number): string {
  return bytesPerSecond === 0 ? '-' : `${formatTorrentSize(bytesPerSecond)}/s`;
}

export function formatTorrentEta(seconds: number): string {
  if (seconds <= 0 || seconds === 8640000) return '-';
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h${minutes}m`;
}

export function torrentStateLabel(state: string, translate: Translate): string {
  const labelKey = STATE_LABELS[state];
  return labelKey ? translate(labelKey) : state;
}

export function torrentStateType(state: string): TorrentStateType {
  if (state.includes('paused') || state.includes('stopped')) return 'neutral';
  if (state === 'downloading' || state === 'forcedDL') return 'success';
  if (state.includes('UP') || state === 'uploading') return 'info';
  if (state === 'error' || state === 'missingFiles') return 'danger';
  return 'info';
}
