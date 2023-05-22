<script lang="ts" setup>
import {
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions,
} from '@headlessui/vue';
import { Down, Up } from '@icon-park/vue-next';
import type { SelectItem } from '#/components';

const props = withDefaults(
  defineProps<{
    modelValue?: SelectItem;
    items: SelectItem[];
  }>(),
  {}
);

const emit = defineEmits(['update:modelValue']);

const selected = ref(props.modelValue || (props.items?.[0] ?? ''));

const otherItems = computed(() => {
  return props?.items?.filter((e) => e.id !== selected.value.id) ?? [];
});

watchEffect(() => {
  emit('update:modelValue', selected.value);
});
</script>

<template>
  <Listbox v-model="selected" v-slot="{ open }">
    <div
      rel
      flex="inline col"
      rounded-6px
      border="1px black"
      text-main
      py-8px
      px-12px
    >
      <ListboxButton bg-transparent fx-cer space-x-24px>
        <div>
          {{ selected?.label ?? selected.value }}
        </div>
        <div :class="[{ hidden: open }]">
          <Down />
        </div>
      </ListboxButton>

      <ListboxOptions mt-8px>
        <div flex="~ items-end" space-x-24px>
          <div flex="~ col" space-y-8px>
            <ListboxOption
              v-slot="{ active }"
              v-for="item in otherItems"
              :key="item.id"
              :value="item"
              :disabled="item.disabled"
            >
              <div
                :class="[
                  { 'text-primary': active },
                  item.disabled ? 'is-disabled' : 'is-btn',
                ]"
              >
                {{ item.label ?? item.value }}
              </div>
            </ListboxOption>
          </div>

          <div :class="[{ hidden: !open }]"><Up /></div>
        </div>
      </ListboxOptions>
    </div>
  </Listbox>
</template>
