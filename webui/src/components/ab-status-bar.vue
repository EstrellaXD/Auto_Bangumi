<script lang="ts" setup>
import {Menu, MenuButton, MenuItem, MenuItems} from '@headlessui/vue';
import {AddOne, International, More} from '@icon-park/vue-next';

withDefaults(
    defineProps<{
      running: boolean;
      items: {
        id: number;
        icon: any;
        label: string | (() => string);
        handle?: () => void | Promise<void>;
      }[];
    }>(),
    {
      running: false,
    }
);

defineEmits<{
  (e: 'changeLang'): void;
  (e: 'clickAdd'): void;
}>();

function abLabel(label: string | (() => string)) {
  if (typeof label === 'function') {
    return label();
  } else {
    return label;
  }
}
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
          <More theme="outline" size="24" fill="#fff"/>
        </MenuButton>

        <ab-status :running="running"/>
      </div>

      <MenuItems
          abs
          top-50px
          left-32px
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
              space-x-8px
              is-btn
              hover:text-white
              hover:bg-primary
              class="group"
              :class="[active ? 'text-white bg-theme-row' : 'text-black']"
              @click="() => i.handle && i.handle()"
          >
            <div
                class="group-hover:text-white"
                :class="[active ? 'text-white' : 'text-primary']"
            >
              <Component :is="i.icon" size="16"></Component>
            </div>
            <div text-main>{{ abLabel(i.label) }}</div>

          </div>
        </MenuItem>
      </MenuItems>
    </div>
  </Menu>
</template>
