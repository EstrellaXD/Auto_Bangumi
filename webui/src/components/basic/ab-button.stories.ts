import type { Meta, StoryObj } from '@storybook/vue3';

import AbButton from './ab-button.vue';

const meta: Meta<typeof AbButton> = {
  title: 'basic/ab-button',
  component: AbButton,
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['primary', 'secondary', 'ghost', 'danger'],
    },
    size: { control: 'select', options: ['sm', 'md'] },
  },
};

export default meta;
type Story = StoryObj<typeof AbButton>;

export const Template: Story = {
  args: { variant: 'primary' },
  render: (args) => ({
    components: { AbButton },
    setup() {
      return { args };
    },
    template: '<ab-button v-bind="args">Add RSS</ab-button>',
  }),
};

export const AllVariants: Story = {
  render: () => ({
    components: { AbButton },
    template: `
      <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center">
        <ab-button variant="primary">Add RSS</ab-button>
        <ab-button variant="secondary">Preview</ab-button>
        <ab-button variant="ghost">Advanced</ab-button>
        <ab-button variant="danger">Delete</ab-button>
        <ab-button variant="primary" disabled>Disabled</ab-button>
        <ab-button variant="primary" loading>Parsing…</ab-button>
        <ab-button variant="secondary" size="sm">Small</ab-button>
      </div>`,
  }),
};
