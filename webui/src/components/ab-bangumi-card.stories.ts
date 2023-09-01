import type { Meta, StoryObj} from "@storybook/vue3";

import AbBangumiCard from "./ab-bangumi-card.vue";

const meta: Meta<typeof AbBangumiCard> = {
    title: "components/ab-bangumi-card",
    component: AbBangumiCard,
}

export default meta;
type Story = StoryObj<typeof AbBangumiCard>;

export const Template: Story = {
    render: (args) => ({
        components: { AbBangumiCard },
        setup() {
            return { args };

        },
        template: '<ab-bangumi-card v-bind="args" />',
    }),
    args: {
        poster: "images/Bangumi/202306/b56b49ea.jpg",
        name: "魔法少女小圆",
        season: 1,
    }

}