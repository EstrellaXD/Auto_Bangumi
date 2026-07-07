/**
 * NexusPHP PT 站点（如 Audiences.me）搜索源 URL 模板构造。
 *
 * NexusPHP 的 torrentrss.php 支持 search 参数，因此 PT 站点可以直接作为
 * AB 的 RSS 型搜索源接入：passkey 放在 URL 里鉴权，linktype=dl 让条目
 * 链接指向 .torrent 下载地址，qBittorrent 可直接抓取。
 *
 * 返回的是后端 search_provider 的 URL 模板：字面量 "%s" 由后端替换为
 * 搜索词，必须保持未编码。
 */

export interface NexusPhpProviderOptions {
  baseUrl: string;
  passkey: string;
  /** NexusPHP 分类 ID（如 Audiences.me 的剧集/动漫为 402），留空则不过滤 */
  categoryId?: string;
}

export function buildNexusPhpSearchUrl(
  options: NexusPhpProviderOptions
): string {
  let base = options.baseUrl.trim().replace(/\/+$/, '');
  if (!/^https?:\/\//i.test(base)) {
    base = `https://${base}`;
  }
  const passkey = encodeURIComponent(options.passkey.trim());
  const cat = options.categoryId?.trim();
  const catParam = cat ? `&cat=${encodeURIComponent(cat)}` : '';
  return `${base}/torrentrss.php?rows=50&linktype=dl&passkey=${passkey}${catParam}&search=%s`;
}
