/**
 * NexusPHP PT 站点（如 Audiences.me）搜索源 URL 模板构造。
 * 生成的模板交给后端 search_provider 使用：后端用 str.replace 把
 * 字面量 "%s" 换成搜索词，因此 %s 必须原样保留、不能被编码。
 */
import { describe, expect, it } from 'vitest';
import { buildNexusPhpSearchUrl } from '../nexusphp';

describe('buildNexusPhpSearchUrl', () => {
  it('should build a torrentrss URL template when given base URL and passkey', () => {
    const url = buildNexusPhpSearchUrl({
      baseUrl: 'https://audiences.me',
      passkey: 'abc123',
    });
    expect(url).toBe(
      'https://audiences.me/torrentrss.php?rows=50&linktype=dl&passkey=abc123&search=%s'
    );
  });

  it('should keep the literal %s placeholder unencoded', () => {
    const url = buildNexusPhpSearchUrl({
      baseUrl: 'https://audiences.me',
      passkey: 'abc123',
    });
    expect(url.endsWith('search=%s')).toBe(true);
  });

  it('should append the cat parameter when a category ID is provided', () => {
    const url = buildNexusPhpSearchUrl({
      baseUrl: 'https://audiences.me',
      passkey: 'abc123',
      categoryId: '402',
    });
    expect(url).toContain('&cat=402&search=%s');
  });

  it('should omit the cat parameter when the category ID is blank', () => {
    const url = buildNexusPhpSearchUrl({
      baseUrl: 'https://audiences.me',
      passkey: 'abc123',
      categoryId: '  ',
    });
    expect(url).not.toContain('cat=');
  });

  it('should strip trailing slashes from the base URL', () => {
    const url = buildNexusPhpSearchUrl({
      baseUrl: 'https://audiences.me/',
      passkey: 'abc123',
    });
    expect(url).toContain('audiences.me/torrentrss.php');
  });

  it('should prepend https scheme when the base URL has none', () => {
    const url = buildNexusPhpSearchUrl({
      baseUrl: 'audiences.me',
      passkey: 'abc123',
    });
    expect(url.startsWith('https://audiences.me/')).toBe(true);
  });

  it('should URL-encode reserved characters in the passkey', () => {
    const url = buildNexusPhpSearchUrl({
      baseUrl: 'https://audiences.me',
      passkey: 'a&b=c',
    });
    expect(url).toContain('passkey=a%26b%3Dc');
  });

  it('should trim surrounding whitespace from inputs', () => {
    const url = buildNexusPhpSearchUrl({
      baseUrl: ' https://audiences.me ',
      passkey: ' abc123 ',
    });
    expect(url).toBe(
      'https://audiences.me/torrentrss.php?rows=50&linktype=dl&passkey=abc123&search=%s'
    );
  });
});
