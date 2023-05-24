<script lang="ts" setup>
import {
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions,
} from '@headlessui/vue';
import { Down, Up } from '@icon-park/vue-next';
import type { SelectItem } from '#/components';
import { isObject, isString } from 'lodash';

const props = withDefaults(
  defineProps<{
    modelValue?: SelectItem | string;
    items: Array<SelectItem | string>;
  }>(),
  {}
);

const emit = defineEmits(['update:modelValue']);

const selected = ref<SelectItem | string>(
  props.modelValue || (props.items?.[0] ?? '')
);

const otherItems = computed(() => {
  return (
    props.items.filter((e) => {
      if (isString(e) && isString(selected.value)) {
        return e !== selected.value;
      } else if (isObject(e) && isObject(selected.value)) {
        return e.id !== selected.value.id;
      }
    }) ?? []
  );
});

const label = computed(() => {
  if (isString(selected.value)) {
    return selected.value;
  } else {
    return selected.value.label ?? selected.value.value;
  }
});

const getLabel = (item: SelectItem | string) => {
  if (isString(item)) {
    return item;
  } else {
    return item.label ?? item.value;
  }
};

const getDisabled = (item: SelectItem | string) => {
  return isString(item) ? false : item.disabled;
};

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
      py-4px
      px-12px
    >
      <ListboxButton bg-transparent fx-cer justify-between space-x-24px>
        <div>
          {{ label }}
        </div>
        <div :class="[{ hidden: open }]">
          <Down />
        </div>
      </ListboxButton>

      <ListboxOptions mt-8px>
        <div flex="~ items-end" justify-between space-x-24px>
          <div flex="~ col" space-y-8px>
            <ListboxOption
              v-slot="{ active }"
              v-for="item in otherItems"
              :key="isString(item) ? item : item.id"
              :value="item"
              :disabled="getDisabled(item)"
            >
              <div
                :class="[
                  { 'text-primary': active },
                  getDisabled(item) ? 'is-disabled' : 'is-btn',
                ]"
              >
                {{ getLabel(item) }}
              </div>
            </ListboxOption>
          </div>

          <div :class="[{ hidden: !open }]"><Up /></div>
        </div>
      </ListboxOptions>
    </div>
  </Listbox>
</template>
