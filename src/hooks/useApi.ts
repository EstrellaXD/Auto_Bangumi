type AnyAsyncFuntion<TData = any> = (...args: any[]) => Promise<TData>;

export function useApi<
  TError = any,
  TApi extends AnyAsyncFuntion = AnyAsyncFuntion,
  TData = ReturnType<TApi>
>(
  api: TApi,
  options?: {
    message?: {
      success?: string;
      error?: string;
    };
  }
) {
  const data = ref<TData>();
  const isLoading = ref(false);

  const fetchResult = createEventHook<TData>();
  const fetchError = createEventHook<TError>();
  const message = useMessage();

  function execute(...params: Parameters<TApi>) {
    isLoading.value = true;

    api(...params)
      .then((res) => {
        data.value = res;
        fetchResult.trigger(res);

        options?.message?.success && message.success(options.message.success);
      })
      .catch((err) => {
        fetchError.trigger(err);

        options?.message?.error && message.error(options.message.error);
      })
      .finally(() => {
        isLoading.value = false;
      });
  }

  return {
    data,
    isLoading,

    execute,
    onResult: fetchResult.on,
    onError: fetchError.on,
  };
}
