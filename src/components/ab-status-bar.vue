<script lang="ts" setup>
import { Menu, MenuButton, MenuItems, MenuItem } from '@headlessui/vue';
import { AddOne, More } from '@icon-park/vue-next';

withDefaults(
  defineProps<{
    running: boolean;
    items: { id: number; icon: any; label: string }[];
  }>(),
  {
    running: false,
  }
);
</script>

<template>
  <Menu>
    <div rel>
      <div fx-cer space-x-16px>
        <add-one theme="outline" size="24" fill="#fff" is-btn btn-click />

        <MenuButton bg-transparent is-btn btn-click>
          <more theme="outline" size="24" fill="#fff" />
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
