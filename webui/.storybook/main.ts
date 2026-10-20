import type { StorybookConfig } from '@storybook/vue3-vite';
import Unocss from 'unocss/vite';

const config: StorybookConfig = {
  stories: ['../src/**/*.mdx', '../src/**/*.stories.@(js|jsx|ts|tsx)'],
  addons: ['@storybook/addon-links', '@storybook/addon-docs'],
  framework: {
    name: '@storybook/vue3-vite',
    options: {},
  },
  viteFinal(config) {
    config.plugins?.push(Unocss());
    // 故事用字符串 template 选项，需要完整版（含编译器）的 vue
    const alias = config.resolve?.alias;
    if (Array.isArray(alias)) {
      config.resolve!.alias = alias.filter(
        (a) => !(a.find instanceof RegExp && a.find.source === '^vue$')
      );
    }
    // Add other configuration here depending on your use case
    return config;
  },
};
export default config;
