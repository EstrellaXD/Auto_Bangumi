/**
 * Composable to manage the Add RSS modal state globally.
 * Allows triggering the Add RSS modal from anywhere in the app.
 */

// Global reactive state (shared across all component instances)
const showAddRss = ref(false);

export function useAddRss() {
  const open = () => {
    showAddRss.value = true;
  };

  const close = () => {
    showAddRss.value = false;
  };

  return {
    showAddRss,
    openAddRss: open,
    closeAddRss: close,
  };
}
