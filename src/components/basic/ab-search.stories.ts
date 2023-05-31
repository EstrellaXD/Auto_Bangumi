import type { Meta, StoryObj } from '@storybook/vue3';

import AbSearch from './ab-search.vue';

const meta: Meta<typeof AbSearch> = {
  title: 'basic/ab-search',
  component: AbSearch,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbSearch>;

export const Template: Story = {
  render: (args) => ({
    components: { AbSearch },
    setup() {
      return { args };
    },
    template: '<ab-search v-bind="args" />',
  }),
};
