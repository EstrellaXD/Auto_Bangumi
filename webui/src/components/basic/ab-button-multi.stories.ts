import type {Meta, StoryObj} from '@storybook/vue3';

import AbButtonMulti from './ab-button-multi.vue';

const meta: Meta<typeof AbButtonMulti> = {
    title: 'basic/ab-button-multi',
    component: AbButtonMulti,
    tags: ['autodocs'],
    argTypes: {
        type: {
            control: {type: 'select'},
            options: ['primary', 'warn'],
        },
        size: {
            control: {type: 'select'},
            options: ['big', 'normal', 'small'],
        },
    },
};

export default meta;
type Story = StoryObj<typeof AbButtonMulti>;

export const Template: Story = {
    render: (args) => ({
        components: {AbButtonMulti},
        setup() {
            return {args};
        },
        template: '<ab-button-multi v-bind="args">button</ab-button-multi>',
    }),
};