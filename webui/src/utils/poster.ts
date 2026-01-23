export function resolvePosterUrl(link: string | null | undefined): string {
  if (!link) return '';
  if (link.startsWith('http://') || link.startsWith('https://')) return link;
  return `/${link}`;
}
