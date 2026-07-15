import { describe, expect, it } from 'vitest';
import {
  getDefaultAuthenticatedPath,
  getMobileNavDestination,
  getRootRedirect,
} from '../mobile-navigation';

describe('getMobileNavDestination', () => {
  it('should select home when the home route is active', () => {
    expect(getMobileNavDestination('/home')).toBe('home');
  });

  it('should select search when the search route is active', () => {
    expect(getMobileNavDestination('/search')).toBe('search');
  });

  it('should select more when a management route is active', () => {
    expect(getMobileNavDestination('/calendar')).toBe('more');
  });

  it('should select more when a nested route is active', () => {
    expect(getMobileNavDestination('/bangumi-torrents/42')).toBe('more');
  });
});

describe('getDefaultAuthenticatedPath', () => {
  it('should select home when the viewport is mobile', () => {
    expect(getDefaultAuthenticatedPath(true)).toBe('/home');
  });

  it('should preserve bangumi when the viewport is not mobile', () => {
    expect(getDefaultAuthenticatedPath(false)).toBe('/bangumi');
  });
});

describe('getRootRedirect', () => {
  it('should redirect the root route to home on a mobile viewport', () => {
    const matchMedia = vi.fn().mockReturnValue({ matches: true });

    expect(getRootRedirect(matchMedia)).toBe('/home');
  });
});
