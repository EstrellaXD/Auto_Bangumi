import type { Meta, StoryObj } from '@storybook/vue3';

import AbList from './ab-list.vue';

const meta: Meta<typeof AbList> = {
  title: 'basic/ab-list',
  component: AbList,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbList>;

export const Template: Story = {
  render: () => ({
    components: { AbList },
    setup() {
      const items = [
        { id: 1, name: '葬送的芙莉莲 第二季', meta: 'Mikan · E08' },
        { id: 2, name: 'Re:从零开始的异世界生活', meta: 'Nyaa · E21' },
        { id: 3, name: '怪兽8号', meta: 'DMHY · E12' },
      ];
      return { items };
    },
    template: `
      <ab-list :items="items" selectable :selected="[1]">
        <template #row="{ item }">
          <div style="display:flex;flex-direction:column;min-width:0">
            <b>{{ item.name }}</b>
            <small style="color:var(--color-text-secondary)">{{ item.meta }}</small>
          </div>
        </template>
      </ab-list>`,
  }),
};
