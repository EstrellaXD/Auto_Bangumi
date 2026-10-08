# LLM Provider (llm_provider)

Adds an LLM parsing provider. `@provider(points.LLM_PROVIDER, id=...)` returns a subclass of `ab_sdk.llm.LLMProviderAdapter`. **The `id` must equal its `info.id`.** The user selects it in Settings → LLM → Provider. You cannot override the id of a built-in provider.

```python
from ab_sdk import Plugin, points, provider
from ab_sdk.llm import AdapterContext, LLMProviderAdapter, ProviderInfo


class MyAdapter(LLMProviderAdapter):
    info = ProviderInfo(
        id="my-llm",
        display_name="My LLM",
        auth_kind="api_key",
        needs_base_url=True,
        default_model="my-model",
    )
    ...  # implement parse / list_models and the other abstract methods


class MyPlugin(Plugin):
    @provider(points.LLM_PROVIDER, id="my-llm")
    def adapter(self):
        return MyAdapter
```

## Notes

- `ProviderInfo` drives the frontend form and the provider list. `auth_kind` is `api_key`, `oauth` or `device_code`.
- An adapter gets the model name, key, `base_url`, timeout and a proxy-aware httpx client factory through `AdapterContext`. It does not read the global configuration.
- A subscription-type provider (`oauth` / `device_code`) implements the auth flow hooks (`AuthChallenge`, `TokenSet`). When the credentials are no longer valid and the refresh fails, raise `AuthExpiredError`. AB then trips the breaker for this provider and sends an `llm_auth_failure` event.
- Existing LLM plugins in the `plugin.json` format (released as `llm-plugins`) still work. New plugins use `plugin.toml` and this extension point.
