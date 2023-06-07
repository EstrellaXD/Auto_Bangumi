import type { Meta, StoryObj } from '@storybook/vue3';

import AbStatus from './ab-status.vue';

const meta: Meta<typeof AbStatus> = {
  title: 'basic/ab-status',
  component: AbStatus,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbStatus>;

export const Template: Story = {
  render: (args) => ({
    components: { AbStatus },
    setup() {
      return { args };
    },
    template: '<ab-status v-bind="args" />',
  }),
};
