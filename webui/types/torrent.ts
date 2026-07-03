export interface Torrent {
  id: number;
  name: string;
  url: string;
  homepage: string | null;
  downloaded: boolean;
  bangumi_id: number | null;
  rss_id: number | null;
  qb_hash: string | null;
}
