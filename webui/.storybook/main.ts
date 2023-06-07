import type { StorybookConfig } from '@storybook/vue3-vite';
import Unocss from 'unocss/vite';

const config: StorybookConfig = {
  stories: ['../src/**/*.mdx', '../src/**/*.stories.@(js|jsx|ts|tsx)'],
  addons: [
    '@storybook/addon-links',
    '@storybook/addon-essentials',
    '@storybook/addon-interactions',
  ],
  framework: {
    name: '@storybook/vue3-vite',
    options: {},
  },
  docs: {
    autodocs: 'tag',
  },
  viteFinal(config) {
    config.plugins?.push(Unocss());
    // Add other configuration here depending on your use case
    return config;
  },
};
export default config;
