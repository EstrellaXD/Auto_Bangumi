import { computed, nextTick, ref } from 'vue';
import { configSectionMatches } from '../config-search';
import en from '@/i18n/en.json';
import zhCN from '@/i18n/zh-CN.json';

const messages = {
  en: {
    'config.parser_set.title': en.config.parser_set.title,
    'config.parser_set.engine': en.config.parser_set.engine,
    'config.parser_set.engine_classic': en.config.parser_set.engine_classic,
    'config.parser_set.engine_tokenizer': en.config.parser_set.engine_tokenizer,
  },
  'zh-CN': {
    'config.parser_set.title': zhCN.config.parser_set.title,
    'config.parser_set.engine': zhCN.config.parser_set.engine,
    'config.parser_set.engine_classic': zhCN.config.parser_set.engine_classic,
    'config.parser_set.engine_tokenizer':
      zhCN.config.parser_set.engine_tokenizer,
  },
} as const;

const parserSection = {
  titleKey: 'config.parser_set.title',
  groups: ['rss_parser'],
  keywords: ['parser', 'engine', 'classic', 'preview', 'tokenizer'],
  keywordKeys: [
    'config.parser_set.engine',
    'config.parser_set.engine_classic',
    'config.parser_set.engine_tokenizer',
  ],
};

describe('configSectionMatches', () => {
  it('matches parser UI text in the current locale and reacts to locale changes', async () => {
    const locale = ref<keyof typeof messages>('zh-CN');
    const query = ref(zhCN.config.parser_set.engine_tokenizer);
    const translate = (key: string) =>
      messages[locale.value][key as keyof (typeof messages)['en']];
    const matches = computed(() =>
      configSectionMatches(parserSection, query.value, translate)
    );

    expect(matches.value).toBe(true);

    locale.value = 'en';
    await nextTick();
    expect(matches.value).toBe(false);

    query.value = en.config.parser_set.engine_tokenizer;
    await nextTick();
    expect(matches.value).toBe(true);
  });

  it('keeps stable aliases searchable in every locale', () => {
    expect(configSectionMatches(parserSection, 'tokenizer', (key) => key)).toBe(
      true
    );
  });
});
