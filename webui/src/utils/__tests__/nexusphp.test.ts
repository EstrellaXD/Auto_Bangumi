/**
 * NexusPHP PT 站点（如 Audiences.me）搜索源 URL 模板构造。
 * 生成的模板交给后端 search_provider 使用：后端用 str.replace 把
 * 字面量 "%s" 换成搜索词，因此 %s 必须原样保留、不能被编码。
 */
import { describe, expect, it } from 'vitest';
import {
  buildNexusPhpSearchUrl,
  isValidNexusPhpCategoryIds,
} from '../nexusphp';

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

  it('should emit a per-category flag when a category ID is provided', () => {
    // 原生 NexusPHP torrentrss.php 只识别 cat<ID>=1 形式的分类参数，
    // 裸 cat=<ID> 会被静默忽略
    const url = buildNexusPhpSearchUrl({
      baseUrl: 'https://audiences.me',
      passkey: 'abc123',
      categoryId: '402',
    });
    expect(url).toContain('&cat402=1&search=%s');
    expect(url).not.toContain('cat=402');
  });

  it('should emit one flag per comma-separated category ID', () => {
    const url = buildNexusPhpSearchUrl({
      baseUrl: 'https://audiences.me',
      passkey: 'abc123',
      categoryId: '402, 403',
    });
    expect(url).toContain('&cat402=1&cat403=1&search=%s');
  });

  it('should omit the cat parameter when the category ID is blank', () => {
    const url = buildNexusPhpSearchUrl({
      baseUrl: 'https://audiences.me',
      passkey: 'abc123',
      categoryId: '  ',
    });
    expect(url).not.toContain('cat');
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

describe('isValidNexusPhpCategoryIds', () => {
  it('should accept an empty input as no filter', () => {
    expect(isValidNexusPhpCategoryIds('')).toBe(true);
    expect(isValidNexusPhpCategoryIds('  ')).toBe(true);
  });

  it('should accept a single numeric ID', () => {
    expect(isValidNexusPhpCategoryIds('402')).toBe(true);
  });

  it('should accept comma-separated numeric IDs with spaces and a trailing comma', () => {
    expect(isValidNexusPhpCategoryIds('402, 403,')).toBe(true);
  });

  it('should reject non-numeric IDs', () => {
    expect(isValidNexusPhpCategoryIds('abc')).toBe(false);
    expect(isValidNexusPhpCategoryIds('402,abc')).toBe(false);
    expect(isValidNexusPhpCategoryIds('4 02')).toBe(false);
  });
});
