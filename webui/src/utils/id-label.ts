import en from '@/i18n/en.json';

/**
 * 把扩展点、权限、重命名方式等内部 id 映射成 i18n 文案：`${group}.${id}`
 * 在 en.json 中存在时返回翻译（id 里的 . 换成 _，避免被当成 key 路径），
 * 未收录的 id（如第三方插件自定义的）原样返回。
 */
export function idLabel(
  t: (key: string) => string,
  group: string,
  id: string
): string {
  const key = `${group}.${id.replaceAll('.', '_')}`;
  const found = key
    .split('.')
    .reduce<unknown>(
      (node, part) => (node as Record<string, unknown> | undefined)?.[part],
      en
    );
  return typeof found === 'string' ? t(key) : id;
}
