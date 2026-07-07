import { defineComponent } from 'vue';
import { mount } from '@vue/test-utils';

/** Run a composable inside a real component instance. */
export function withSetup<T>(fn: () => T): T {
  let result!: T;
  mount(
    defineComponent({
      setup() {
        result = fn();
        return () => null;
      },
    })
  );
  return result;
}
