export interface NotificationData {
  key?: string;
  id: string;
  title: string;
  content: string;
  datetime: string;
  has_read: boolean;
}

/**
 * API Response
 */
export interface WithTotal {
  total: number;
}

export interface WithTotalAndMessages {
  total: number;
  messages: NotificationData[];
}

export interface NotificationResponse {
  code: number;
  msg: string;
  data?: WithTotal | WithTotalAndMessages;
}
