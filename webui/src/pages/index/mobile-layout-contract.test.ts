import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

function readSource(relativePath: string): string {
  return readFileSync(new URL(relativePath, import.meta.url), 'utf8');
}

describe('mobile library layout contract', () => {
  it('should lock the Bangumi poster grid to two columns below 640px', () => {
    const source = readSource('./bangumi.vue');

    expect(source).toMatch(
      /@media screen and \(max-width: 639px\)[\s\S]*?\.bangumi-grid\s*\{[\s\S]*?grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/
    );
  });

  it('should scope torrent mobile layout to the strict phone breakpoint', () => {
    const source = readSource('../../components/ab-torrent-list-page.vue');

    expect(source).toMatch(
      /@media screen and \(max-width: 639px\)[\s\S]*?\.torrent-selection-toolbar/
    );
  });

  it('should scope compact calendar controls to the strict phone breakpoint', () => {
    const source = readSource('./calendar.vue');

    expect(source).toMatch(
      /@media screen and \(max-width: 639px\)[\s\S]*?\.calendar-refresh-btn/
    );
  });

  it('should scope compact RSS controls to the strict phone breakpoint', () => {
    const source = readSource('./rss.vue');

    expect(source).toMatch(
      /@media screen and \(max-width: 639px\)[\s\S]*?\.rss-selection-toolbar/
    );
  });

  it('should keep the calendar rule picker within a 320px sheet', () => {
    const source = readSource(
      '../../components/calendar/calendar-rule-list-popup.vue'
    );

    expect(source).toMatch(
      /@media screen and \(max-width: 639px\)[\s\S]*?\.rule-list\s*\{[\s\S]*?min-width:\s*min\(300px, 100%\)/
    );
  });

  it('should make the advanced disclosure a phone-sized touch target', () => {
    const source = readSource('../../components/advanced-section.vue');

    expect(source).toMatch(
      /@media screen and \(max-width: 639px\)[\s\S]*?\.advanced-toggle[\s\S]*?min-height:\s*var\(--touch-target\)/
    );
  });
});
