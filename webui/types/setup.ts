export interface SetupStatus {
  need_setup: boolean;
  version: string;
}

export interface TestDownloaderRequest {
  type: string;
  host: string;
  username: string;
  password: string;
  ssl: boolean;
}

export interface TestRSSRequest {
  url: string;
}

export interface TestNotificationRequest {
  type: string;
  token: string;
  chat_id: string;
}

export interface TestResult {
  success: boolean;
  message_en: string;
  message_zh: string;
  title?: string;
  item_count?: number;
}

export interface SetupCompleteRequest {
  username: string;
  password: string;
  downloader_type: string;
  downloader_host: string;
  downloader_username: string;
  downloader_password: string;
  downloader_path: string;
  downloader_ssl: boolean;
  rss_url: string;
  rss_name: string;
  notification_enable: boolean;
  notification_type: string;
  notification_token: string;
  notification_chat_id: string;
}

export type WizardStep =
  | 'welcome'
  | 'account'
  | 'downloader'
  | 'rss'
  | 'media'
  | 'notification'
  | 'review';
