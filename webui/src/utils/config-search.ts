interface SearchableConfigSection {
  titleKey: string;
  groups: readonly string[];
  keywords: readonly string[];
  keywordKeys?: readonly string[];
}

/** Match a settings section against stable aliases and current-locale UI text. */
export function configSectionMatches(
  section: SearchableConfigSection,
  rawQuery: string,
  translate: (key: string) => string
): boolean {
  const query = rawQuery.trim().toLowerCase();
  if (!query) return true;

  const localizedText = [section.titleKey, ...(section.keywordKeys ?? [])].map(
    translate
  );
  return [...localizedText, ...section.keywords, ...section.groups].some(
    (text) => text.toLowerCase().includes(query)
  );
}
