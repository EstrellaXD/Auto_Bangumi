<script lang="ts" setup>
import {
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions,
} from '@headlessui/vue';
import { Down, Up } from '@icon-park/vue-next';
import { isObject, isString } from 'radash';
import type { SelectItem } from '#/components';

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
      } else {
        return false;
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

function getLabel(item: SelectItem | string) {
  if (isString(item)) {
    return item;
  } else {
    return item.label ?? item.value;
  }
}

function getDisabled(item: SelectItem | string) {
  return isString(item) ? false : item.disabled;
}

watchEffect(() => {
  emit('update:modelValue', selected.value);
});
</script>

<template>
  <Listbox v-slot="{ open }" v-model="selected">
    <div class="select-wrapper">
      <ListboxButton class="select-button">
        <div class="select-value">{{ label }}</div>
        <div :class="[{ hidden: open }]">
          <Down :size="14" />
        </div>
      </ListboxButton>

      <ListboxOptions class="select-options">
        <div class="select-options-inner">
          <div class="select-options-list">
            <ListboxOption
              v-for="item in otherItems"
              v-slot="{ active }"
              :key="isString(item) ? item : item.id"
              :value="item"
              :disabled="getDisabled(item)"
            >
              <div
                class="select-option"
                :class="[
                  active && 'select-option--active',
                  getDisabled(item) && 'select-option--disabled',
                ]"
              >
                {{ getLabel(item) }}
              </div>
            </ListboxOption>
          </div>

          <div :class="[{ hidden: !open }]"><Up :size="14" /></div>
        </div>
      </ListboxOptions>
    </div>
  </Listbox>
</template>

<style lang="scss" scoped>
.select-wrapper {
  position: relative;
  display: inline-flex;
  flex-direction: column;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  font-size: 12px;
  padding: 4px 12px;
  transition: border-color var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
  }
}

.select-button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--color-text);
  padding: 0;
}

.select-value {
  color: var(--color-text);
}

.select-options {
  margin-top: 8px;
}

.select-options-inner {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.select-options-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.select-option {
  cursor: pointer;
  user-select: none;
  color: var(--color-text-secondary);
  transition: color var(--transition-fast);

  &--active {
    color: var(--color-primary);
  }

  &--disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }
}
</style>
