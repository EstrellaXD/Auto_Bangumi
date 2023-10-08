export interface RSS {
  id: number;
  name: string;
  url: string;
  aggregate: boolean;
  parser: string;
  enabled: boolean;
}

export const rssTemplate: RSS = {
  id: 0,
  name: '',
  url: '',
  aggregate: false,
  parser: '',
  enabled: false,
};
