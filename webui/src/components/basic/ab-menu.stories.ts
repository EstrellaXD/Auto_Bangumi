import type { Meta, StoryObj } from '@storybook/vue3';

import AbButton from './ab-button.vue';
import AbMenu from './ab-menu.vue';

const meta: Meta<typeof AbMenu> = {
  title: 'basic/ab-menu',
  component: AbMenu,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbMenu>;

export const Template: Story = {
  args: {
    items: [
      { key: 'enable', label: 'Enable rule' },
      { key: 'archive', label: 'Archive rule' },
      { key: 'delete', label: 'Delete rule', danger: true },
    ],
  },
  render: (args) => ({
    components: { AbMenu, AbButton },
    setup() {
      return { args };
    },
    template: `
      <ab-menu v-bind="args">
        <template #trigger>
          <ab-button variant="secondary">Actions</ab-button>
        </template>
      </ab-menu>`,
  }),
};
