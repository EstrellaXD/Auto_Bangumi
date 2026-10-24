import antfu from '@antfu/eslint-config';
import storybook from 'eslint-plugin-storybook';

export default antfu(
  {
    vue: true,
    stylistic: { semi: true, quotes: 'single', indent: 2, braceStyle: '1tbs' },
    ignores: [
      '/build',
      '/dist',
      '/e2e/.auth',
      '/playwright-report',
      '/test-results',
    ],
  },
  {
    rules: {
      'antfu/if-newline': 'off',
      'style/operator-linebreak': ['error', 'after', { overrides: { '?': 'before', ':': 'before', '|>': 'before' } }],
      'style/quote-props': ['error', 'as-needed'],
      'style/multiline-comment-style': 'off',
      'node/prefer-global/process': 'off',
      'regexp/no-super-linear-backtracking': 'off',
      'regexp/no-unused-capturing-group': 'off',
      'unicorn/prefer-dom-node-text-content': 'off',
      'vue/no-required-prop-with-default': 'off',
      'ts/no-empty-object-type': 'off',
      'unused-imports/no-unused-vars': 'warn',
      'antfu/curly': 'off',
      curly: 'off',
      'test/prefer-lowercase-title': 'off',
      'import/consistent-type-specifier-style': 'off',
      'style/arrow-parens': ['error', 'always'],
      'style/comma-dangle': ['error', { arrays: 'always-multiline', objects: 'always-multiline', imports: 'always-multiline', exports: 'always-multiline', functions: 'never' }],
      'perfectionist/sort-imports': 'off',
      'perfectionist/sort-named-imports': 'off',
      'import/order': 'off',
      'no-console': 'off',
      'vue/custom-event-name-casing': 'off',
    },
  },
  {
    files: ['public/sw.js'],
    rules: { 'no-restricted-globals': 'off' },
  },
  ...storybook.configs['flat/recommended']
);
