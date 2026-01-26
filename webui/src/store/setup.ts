import type { SetupCompleteRequest, WizardStep } from '#/setup';

export const useSetupStore = defineStore('setup', () => {
  const steps: WizardStep[] = [
    'welcome',
    'account',
    'downloader',
    'rss',
    'notification',
    'review',
  ];

  const currentStepIndex = ref(0);
  const currentStep = computed(() => steps[currentStepIndex.value]);
  const isLoading = ref(false);

  // Form data
  const accountData = reactive({
    username: '',
    password: '',
    confirmPassword: '',
  });

  const downloaderData = reactive({
    type: 'qbittorrent',
    host: '',
    username: '',
    password: '',
    path: '/downloads/Bangumi',
    ssl: false,
  });

  const rssData = reactive({
    url: '',
    name: '',
    skipped: false,
  });

  const notificationData = reactive({
    enable: false,
    type: 'telegram',
    token: '',
    chat_id: '',
    skipped: false,
  });

  // Validation states
  const validation = reactive({
    downloaderTested: false,
    rssTested: false,
    notificationTested: false,
  });

  // Navigation
  function nextStep() {
    if (currentStepIndex.value < steps.length - 1) {
      currentStepIndex.value++;
    }
  }

  function prevStep() {
    if (currentStepIndex.value > 0) {
      currentStepIndex.value--;
    }
  }

  function goToStep(index: number) {
    if (index >= 0 && index < steps.length) {
      currentStepIndex.value = index;
    }
  }

  // Build final request
  function buildCompleteRequest(): SetupCompleteRequest {
    return {
      username: accountData.username,
      password: accountData.password,
      downloader_type: downloaderData.type,
      downloader_host: downloaderData.host,
      downloader_username: downloaderData.username,
      downloader_password: downloaderData.password,
      downloader_path: downloaderData.path,
      downloader_ssl: downloaderData.ssl,
      rss_url: rssData.skipped ? '' : rssData.url,
      rss_name: rssData.skipped ? '' : rssData.name,
      notification_enable: !notificationData.skipped && notificationData.enable,
      notification_type: notificationData.type,
      notification_token: notificationData.token,
      notification_chat_id: notificationData.chat_id,
    };
  }

  function $reset() {
    currentStepIndex.value = 0;
    isLoading.value = false;
    Object.assign(accountData, { username: '', password: '', confirmPassword: '' });
    Object.assign(downloaderData, {
      type: 'qbittorrent',
      host: '',
      username: '',
      password: '',
      path: '/downloads/Bangumi',
      ssl: false,
    });
    Object.assign(rssData, { url: '', name: '', skipped: false });
    Object.assign(notificationData, {
      enable: false,
      type: 'telegram',
      token: '',
      chat_id: '',
      skipped: false,
    });
    Object.assign(validation, {
      downloaderTested: false,
      rssTested: false,
      notificationTested: false,
    });
  }

  return {
    steps,
    currentStepIndex,
    currentStep,
    isLoading,
    accountData,
    downloaderData,
    rssData,
    notificationData,
    validation,
    nextStep,
    prevStep,
    goToStep,
    buildCompleteRequest,
    $reset,
  };
});
