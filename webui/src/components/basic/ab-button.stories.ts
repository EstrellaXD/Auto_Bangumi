import type { Meta, StoryObj } from '@storybook/vue3';

import AbButton from './ab-button.vue';

const meta: Meta<typeof AbButton> = {
  title: 'basic/ab-button',
  component: AbButton,
  tags: ['autodocs'],
  argTypes: {
    type: {
      control: { type: 'select' },
      options: ['primary', 'warn'],
    },
    size: {
      control: { type: 'select' },
      options: ['big', 'normal', 'small'],
    },
  },
};

export default meta;
type Story = StoryObj<typeof AbButton>;

export const Template: Story = {
  render: (args) => ({
    components: { AbButton },
    setup() {
      return { args };
    },
    template: '<ab-button v-bind="args">button</ab-button>',
  }),
};
