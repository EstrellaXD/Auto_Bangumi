
C = TypeVar("C", bound=BaseModel)

_plugins: dict[str, "Plugin"] = {}
_managers: list["PluginManager"] = []

def _module_name_to_plugin_id(
    module_name: str, controlled_modules: Optional[dict[str, str]] = None
) -> str:
    plugin_name = _module_name_to_plugin_name(module_name)
    if parent_plugin_id := _find_parent_plugin_id(module_name, controlled_modules):
        return f"{parent_plugin_id}:{plugin_name}"
    return plugin_name
