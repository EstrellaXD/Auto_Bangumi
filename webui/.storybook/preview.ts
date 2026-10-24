import type { Preview } from '@storybook/vue3-vite';
import '@unocss/reset/tailwind-compat.css';
import 'virtual:uno.css';

const preview: Preview = {
  parameters: {
    actions: { argTypesRegex: '^on[A-Z].*' },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/,
      },
    },
  },
};

export default preview;
