import { createGenerator } from 'unocss';
import { describe, expect, it } from 'vitest';
import unoConfig from '../../unocss.config';

describe('RSS refresh icon', () => {
  it('generates a visible icon with the production UnoCSS configuration', async () => {
    const uno = createGenerator(unoConfig);
    const { css, matched } = await uno.generate('i-carbon-renew');

    expect(matched.has('i-carbon-renew')).toBe(true);
    expect(css).toContain('data:image/svg+xml');
    expect(css).toMatch(/width:\s*1em/);
    expect(css).toMatch(/height:\s*1em/);
  });
});
