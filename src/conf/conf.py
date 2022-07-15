import os
from conf import const


class Settings(dict):
    def __getattr__(self, item):
        return self.get(item)

    def __setattr__(self, key, value):
        self[key] = value

    def init(self, args=None):
        self.update(self._settings_from_env())
        if args:
            self.update(args)

    def _val_from_env(self, env, attr):
        """Transforms env-strings to python."""
        val = os.environ[env]
        if isinstance(attr, tuple):
            conv_func = attr[1]
            val = conv_func(val)
        return val

    def _settings_from_env(self):
        """Loads settings from env."""
        return {
            attr if isinstance(attr, str) else attr[0]: self._val_from_env(env, attr)
            for env, attr in const.ENV_TO_ATTR.items()
            if env in os.environ
        }


settings = Settings(const.DEFAULT_SETTINGS)