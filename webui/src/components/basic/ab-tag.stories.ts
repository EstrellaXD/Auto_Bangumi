import type { Meta, StoryObj } from '@storybook/vue3';

import AbTag from './ab-tag.vue';

const meta: Meta<typeof AbTag> = {
  title: 'basic/ab-tag',
  component: AbTag,
  tags: ['autodocs'],
  argTypes: {
    type: {
      control: 'select',
      options: ['success', 'warning', 'danger', 'info', 'neutral'],
    },
  },
};

export default meta;
type Story = StoryObj<typeof AbTag>;

export const Template: Story = {
  args: { type: 'success', title: 'Airing' },
  render: (args) => ({
    components: { AbTag },
    setup() {
      return { args };
    },
    template: '<ab-tag v-bind="args" />',
  }),
};

export const AllTypes: Story = {
  render: () => ({
    components: { AbTag },
    template: `
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <ab-tag type="success" title="Airing" />
        <ab-tag type="neutral" title="Archived" />
        <ab-tag type="info" title="S02E08" />
        <ab-tag type="warning" title="Needs review" />
        <ab-tag type="danger" title="Parse failed" />
        <ab-tag type="info" title="葬送的芙莉莲 第二季" closable />
        <ab-tag type="neutral" title="桜都字幕组 · 简日双语 · 1080p" />
      </div>`,
  }),
};
