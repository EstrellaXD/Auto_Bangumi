import type { Meta, StoryObj } from '@storybook/vue3';

import AbEmpty from './ab-empty.vue';

const meta: Meta<typeof AbEmpty> = {
  title: 'basic/ab-empty',
  component: AbEmpty,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbEmpty>;

export const Template: Story = {
  args: {
    title: 'No RSS rules yet',
    description:
      'Add a feed and AutoBangumi starts organizing new episodes automatically.',
  },
  render: (args) => ({
    components: { AbEmpty },
    setup() {
      return { args };
    },
    template: '<ab-empty v-bind="args" />',
  }),
};
