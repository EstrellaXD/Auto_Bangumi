export type MobileNavDestination = 'home' | 'search' | 'more';

export function getMobileNavDestination(path: string): MobileNavDestination {
  if (path === '/home') return 'home';
  if (path === '/search') return 'search';
  return 'more';
}

export function getDefaultAuthenticatedPath(isMobile: boolean) {
  return isMobile ? ('/home' as const) : ('/bangumi' as const);
}

export function getRootRedirect(
  matchMedia: (
    query: string
  ) => Pick<MediaQueryList, 'matches'> = window.matchMedia.bind(window)
) {
  return getDefaultAuthenticatedPath(matchMedia('(max-width: 639px)').matches);
}
