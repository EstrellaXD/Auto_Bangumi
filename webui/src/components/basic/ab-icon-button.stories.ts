import type { Meta, StoryObj } from '@storybook/vue3-vite';
import { CirclePlus, Pencil, Trash } from '@lucide/vue';

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
    components: { AbIconButton, CirclePlus },
    setup() {
      return { args };
    },
    template: '<ab-icon-button v-bind="args"><circle-plus /></ab-icon-button>',
  }),
};

export const Row: Story = {
  render: () => ({
    components: { AbIconButton, CirclePlus, Pencil, Trash },
    template: `
      <div style="display:flex;gap:4px">
        <ab-icon-button label="Add"><circle-plus /></ab-icon-button>
        <ab-icon-button label="Edit"><pencil /></ab-icon-button>
        <ab-icon-button label="Delete"><trash /></ab-icon-button>
        <ab-icon-button label="Disabled" disabled><pencil /></ab-icon-button>
        <ab-icon-button label="Small" size="sm"><pencil /></ab-icon-button>
      </div>`,
  }),
};
