export function resolvePosterUrl(link: string | null | undefined): string {
  if (!link) return '';
  if (link.startsWith('http://') || link.startsWith('https://')) return link;
  const base = window.__BASE_PATH__ || '';
  return link.startsWith('/') ? `${base}${link}` : `${base}/${link}`;
}
