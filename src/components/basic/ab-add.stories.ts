import type { Meta, StoryObj } from '@storybook/vue3';

import AbAdd from './ab-add.vue';

const meta: Meta<typeof AbAdd> = {
  title: 'basic/ab-add',
  component: AbAdd,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbAdd>;

export const Template: Story = {
  render: (args) => ({
    components: { AbAdd },
    setup() {
      return { args };
    },
    template: '<ab-add v-bind="args"></ab-add>',
  }),
};
