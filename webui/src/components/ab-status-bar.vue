<script lang="ts" setup>
import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/vue';
import { AddOne, More, International } from '@icon-park/vue-next';

withDefaults(
  defineProps<{
    running: boolean;
    items: {
      id: number;
      icon: any;
      label: string;
      handle?: () => void | Promise<void>;
    }[];
  }>(),
  {
    running: false,
  }
);

defineEmits(['clickAdd']);
</script>

<template>
  <Menu>
    <div rel>
      <div fx-cer space-x-16px>
        <International
          theme="outline"
          size="24"
          fill="#fff"
          is-btn
          btn-click
          @click="() => $emit('changeLang')"
        />

        <AddOne
          theme="outline"
          size="24"
          fill="#fff"
          is-btn
          btn-click
          @click="() => $emit('clickAdd')"
        />

        <MenuButton bg-transparent is-btn btn-click>
          <More theme="outline" size="24" fill="#fff" />
        </MenuButton>

        <ab-status :running="running" />
      </div>

      <MenuItems
        abs
        top-50px
        w-120px
        rounded-8px
        bg-white
        overflow-hidden
        shadow
        z-99
      >
        <MenuItem v-for="i in items" :key="i.id" v-slot="{ active }">
          <div
            w-full
            h-32px
            px-12px
            fx-cer
            justify-between
            is-btn
            hover:text-white
            hover:bg-primary
            class="group"
            :class="[active ? 'text-white bg-theme-row' : 'text-black']"
            @click="() => i.handle && i.handle()"
          >
            <div text-main>{{ i.label }}</div>

            <div
              class="group-hover:text-white"
              :class="[active ? 'text-white' : 'text-primary']"
            >
              <Component :is="i.icon" size="16"></Component>
            </div>
          </div>
        </MenuItem>
      </MenuItems>
    </div>
  </Menu>
</template>
