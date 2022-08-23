import os
from conf import const
from utils import json_config


class Settings(dict):
    def __getattr__(self, item):
        return self.get(item)

    def __setattr__(self, key, value):
        self[key] = value

    def init(self, args=None):
        self.update(self._settings_from_env())
        self.update(self._settings_from_json())
        if args:
            self.update(args)

    def save_settings(self):
        save_data = {
            key : value
            for key, value in self.items()
            if not key in const.INTERNAL_SETTINGS
        }
        json_config.save(self.setting_path, save_data)

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

    def _settings_from_json(self):
        """Loads settings from setting.json."""
        if os.path.exists(self.setting_path):
            setting_data = json_config.load(self.setting_path)
            return {
                key : value
                for key, value in setting_data.items()
                if not key in const.INTERNAL_SETTINGS
            }
        else:
            self.save_settings()
        return {}

settings = Settings(const.DEFAULT_SETTINGS)