import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

function pageSource(name: string): string {
  return readFileSync(
    fileURLToPath(new URL(`../${name}.vue`, import.meta.url)),
    'utf8'
  );
}

describe('mobile media page layouts', () => {
  it('should scope downloader layout changes to phone widths', () => {
    expect(pageSource('downloader')).toContain(
      '@media screen and (max-width: 639px)'
    );
  });

  it('should preserve the existing downloader action bar on tablets', () => {
    expect(pageSource('downloader')).toContain(
      '@media screen and (min-width: 640px) and (max-width: 1023px)'
    );
  });

  it('should scope player layout changes to phone widths', () => {
    expect(pageSource('player')).toContain(
      '@media screen and (max-width: 639px)'
    );
  });

  it('should scope log layout changes to phone widths', () => {
    expect(pageSource('log')).toContain('@media screen and (max-width: 639px)');
  });
});
