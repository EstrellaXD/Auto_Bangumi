/**
 * NexusPHP PT 站点（如 Audiences.me）搜索源 URL 模板构造。
 *
 * NexusPHP 的 torrentrss.php 用 passkey 放在 URL 里鉴权，linktype=dl 让
 * 条目链接指向 .torrent 下载地址，qBittorrent 可直接抓取。
 *
 * 注意：原生（新版）NexusPHP 已停用 torrentrss.php 的 search 参数
 * （源码中写死 `$searchstr = null`），此时该模板对任何搜索词都返回
 * 最新种子；只有保留了 search 支持的站点/分支能真正按词过滤。UI 的
 * 提示文案要求用户自行在站点上验证。
 *
 * 分类参数必须用 cat<ID>=1 的逐分类开关形式（torrentrss.php 只识别
 * /^(cat|sou|med|...)\d+$/ 形式的参数），裸 cat=<ID> 会被静默忽略。
 *
 * 返回的是后端 search_provider 的 URL 模板：字面量 "%s" 由后端替换为
 * 搜索词，必须保持未编码。
 */

export interface NexusPhpProviderOptions {
  baseUrl: string;
  passkey: string;
  /** NexusPHP 分类 ID（如 Audiences.me 的剧集/动漫为 402），可用逗号
   *  分隔多个；留空则不过滤 */
  categoryId?: string;
}

function parseCategoryIds(input: string | undefined): string[] {
  return (input ?? '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

/** 分类 ID 输入校验：空 = 不过滤；否则每个逗号分隔段都必须是纯数字 */
export function isValidNexusPhpCategoryIds(input: string): boolean {
  return parseCategoryIds(input).every((id) => /^\d+$/.test(id));
}

export function buildNexusPhpSearchUrl(
  options: NexusPhpProviderOptions
): string {
  let base = options.baseUrl.trim().replace(/\/+$/, '');
  if (!/^https?:\/\//i.test(base)) {
    base = `https://${base}`;
  }
  const passkey = encodeURIComponent(options.passkey.trim());
  const catParams = parseCategoryIds(options.categoryId)
    .map((id) => `&cat${encodeURIComponent(id)}=1`)
    .join('');
  return `${base}/torrentrss.php?rows=50&linktype=dl&passkey=${passkey}${catParams}&search=%s`;
}
