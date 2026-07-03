type AnyAsyncFunction<TData = any> = (...args: any[]) => Promise<TData>;

export type ApiExecuteResult<TData> =
  | { ok: true; data: TData }
  | { ok: false; error: unknown };

interface Options<T = any> {
  showMessage?: boolean;
  onBeforeExecute?: () => void;
  onSuccess?: (data: T) => void;
  onError?: (error: any) => void;
  onFinally?: () => void;
}

export function useApi<
  TApi extends AnyAsyncFunction = AnyAsyncFunction,
  TData = Awaited<ReturnType<TApi>>
>(
  api: TApi,
  {
    showMessage = true,
    onBeforeExecute,
    onSuccess,
    onError,
    onFinally,
  }: Options<TData> = {}
) {
  const data = ref<TData>();
  const isLoading = ref(false);

  const message = useMessage();
  const { returnUserLangMsg } = useMyI18n();

  async function execute(
    ...params: Parameters<TApi>
  ): Promise<ApiExecuteResult<TData>> {
    onBeforeExecute?.();

    try {
      isLoading.value = true;
      const res = await api(...params);
      data.value = res as TData;

      onSuccess?.(res as TData);

      if (showMessage && res && typeof res === 'object' && 'msg_en' in res) {
        message.success(returnUserLangMsg(res));
      }
      return { ok: true, data: res as TData };
    } catch (err) {
      onError?.(err);
      return { ok: false, error: err };
    } finally {
      isLoading.value = false;
      onFinally?.();
    }
  }

  return {
    data,
    isLoading,

    execute,
  };
}
