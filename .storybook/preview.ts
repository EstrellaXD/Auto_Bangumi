import type { Preview } from '@storybook/vue3';
import '@unocss/reset/tailwind-compat.css';
import 'uno.css';

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
