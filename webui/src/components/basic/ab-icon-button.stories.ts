import type { Meta, StoryObj } from '@storybook/vue3';
import { AddOne, Delete, Edit } from '@icon-park/vue-next';

import AbIconButton from './ab-icon-button.vue';

const meta: Meta<typeof AbIconButton> = {
  title: 'basic/ab-icon-button',
  component: AbIconButton,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbIconButton>;

export const Template: Story = {
  args: { label: 'Add' },
  render: (args) => ({
    components: { AbIconButton, AddOne },
    setup() {
      return { args };
    },
    template: '<ab-icon-button v-bind="args"><add-one /></ab-icon-button>',
  }),
};

export const Row: Story = {
  render: () => ({
    components: { AbIconButton, AddOne, Edit, Delete },
    template: `
      <div style="display:flex;gap:4px">
        <ab-icon-button label="Add"><add-one /></ab-icon-button>
        <ab-icon-button label="Edit"><edit /></ab-icon-button>
        <ab-icon-button label="Delete"><delete /></ab-icon-button>
        <ab-icon-button label="Disabled" disabled><edit /></ab-icon-button>
        <ab-icon-button label="Small" size="sm"><edit /></ab-icon-button>
      </div>`,
  }),
};
