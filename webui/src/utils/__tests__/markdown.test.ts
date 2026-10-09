import { describe, expect, it } from 'vitest';
import { renderMarkdown } from '../markdown';

describe('renderMarkdown', () => {
  it.each([
    ['# Title', '<h3>Title</h3>'],
    ['### Deep ###', '<h5>Deep</h5>'],
    ['one\ntwo\n\nthree', '<p>one two</p><p>three</p>'],
    ['- a\n- b', '<ul><li>a</li><li>b</li></ul>'],
    ['1. a\n2) b', '<ol><li>a</li><li>b</li></ol>'],
    ['- a\n  more\n\n1. b', '<ul><li>a more</li></ul><ol><li>b</li></ol>'],
    ['text\n- a', '<p>text</p><ul><li>a</li></ul>'],
    ['**b** and *i*', '<p><strong>b</strong> and <em>i</em></p>'],
    ['__b__ _i_ media_id', '<p><strong>b</strong> <em>i</em> media_id</p>'],
    ['use `a **b**`', '<p>use <code>a **b**</code></p>'],
    [
      '```toml\nid = 1 # *x*\n\n<b>\n```',
      '<pre><code>id = 1 # *x*\n\n&lt;b&gt;</code></pre>',
    ],
    ['```\nopen', '<pre><code>open</code></pre>'],
    [
      '[docs](https://a.io/x_y_z)',
      '<p><a href="https://a.io/x_y_z" target="_blank" rel="noopener noreferrer">docs</a></p>',
    ],
  ])('should render %j', (source, html) => {
    expect(renderMarkdown(source)).toBe(html);
  });

  it.each([
    [
      '<script>alert(1)</script>',
      '<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>',
    ],
    [
      '<img src=x onerror="alert(1)">',
      '<p>&lt;img src=x onerror=&quot;alert(1)&quot;&gt;</p>',
    ],
    ['[x](javascript:alert(1))', '<p>x)</p>'],
    ['[x](JavaScript:alert`1`)', '<p>x</p>'],
    ['[x](data:text/html,hi)', '<p>x</p>'],
    ['![pic](https://a.io/p.png)', '<p>pic</p>'],
    ['# <iframe src=x>', '<h3>&lt;iframe src=x&gt;</h3>'],
  ])('should neutralise %j', (source, html) => {
    expect(renderMarkdown(source)).toBe(html);
  });

  it('should keep a quote in a link URL inside the href attribute', () => {
    const host = document.createElement('div');
    host.innerHTML = renderMarkdown('[x](https://a.io"onmouseover="alert(1))');
    const link = host.querySelector('a');
    expect(link?.getAttributeNames().sort()).toEqual(['href', 'rel', 'target']);
    expect(link?.getAttribute('href')).toBe(
      'https://a.io"onmouseover="alert(1'
    );
  });

  it('should produce no element other than the allowed tags', () => {
    const host = document.createElement('div');
    host.innerHTML = renderMarkdown(
      '<svg onload=alert(1)>\n\n<a href="javascript:x">y</a>\n\n**<b>z</b>**'
    );
    const tags = Array.from(host.querySelectorAll('*'), (el) => el.tagName);
    expect(tags).toEqual(['P', 'P', 'P', 'STRONG']);
  });
});
