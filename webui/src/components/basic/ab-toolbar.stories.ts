import type { Meta, StoryObj } from '@storybook/vue3';

import AbToolbar from './ab-toolbar.vue';

const meta: Meta<typeof AbToolbar> = {
  title: 'basic/ab-toolbar',
  component: AbToolbar,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbToolbar>;

export const Template: Story = {
  render: () => ({
    components: { AbToolbar },
    template: `
      <ab-toolbar>
        <template #search>
          <input style="width:100%;height:32px" placeholder="Search…" />
        </template>
        <template #actions>
          <button>Add RSS</button>
        </template>
      </ab-toolbar>`,
  }),
};
