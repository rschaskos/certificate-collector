"""
Configuration loader for Certificate Collector v4.0
"""

import json
from pathlib import Path
from typing import Dict, Any
from core.logger import get_logger


class Config:
    """Configuration manager that loads and validates config.json."""

    _instance = None
    _config_data = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_path: str = 'config.json'):
        if self._config_data is None:
            self.logger = get_logger('Config')
            self.config_path = Path(config_path)
            self._load_config()

    def _load_config(self):
        """Load configuration from JSON file."""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f'Configuration file not found: {self.config_path}')

            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_data = json.load(f)

            self.logger.info(f'Configuration loaded successfully from {self.config_path}')
            self._validate_config()

        except json.JSONDecodeError as e:
            self.logger.error(f'Invalid JSON in config file: {e}')
            raise
        except Exception as e:
            self.logger.error(f'Failed to load configuration: {e}')
            raise

    def _validate_config(self):
        """Validate required configuration keys."""
        required_keys = ['urls', 'selectors', 'timeouts', 'paths', 'settings']

        for key in required_keys:
            if key not in self._config_data:
                raise ValueError(f'Missing required configuration key: {key}')

        # Validate paths exist or create them
        for path_key, path_value in self._config_data['paths'].items():
            path = Path(path_value)
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                self.logger.info(f'Created directory: {path}')

        self.logger.debug('Configuration validation passed')

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports nested keys with dot notation)."""
        keys = key.split('.')
        value = self._config_data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_url(self, certificate_type: str) -> str:
        """Get URL for specific certificate type."""
        return self.get(f'urls.{certificate_type}')

    def get_selectors(self, certificate_type: str) -> Dict[str, str]:
        """Get selectors for specific certificate type."""
        return self.get(f'selectors.{certificate_type}', {})

    def get_timeout(self, timeout_type: str = 'default_wait') -> int:
        """Get timeout value in milliseconds."""
        return self.get(f'timeouts.{timeout_type}', 10000)

    def get_path(self, path_type: str) -> Path:
        """Get path as Path object."""
        path_str = self.get(f'paths.{path_type}', './')
        return Path(path_str)

    def get_setting(self, setting_name: str, default: Any = None) -> Any:
        """Get application setting."""
        return self.get(f'settings.{setting_name}', default)

    @property
    def version(self) -> str:
        """Get configuration version."""
        return self.get('version', '4.0')

    @property
    def all_certificate_types(self) -> list:
        """Get list of all available certificate types."""
        return list(self._config_data.get('urls', {}).keys())

    def reload(self):
        """Reload configuration from file."""
        self._config_data = None
        self._load_config()
        self.logger.info('Configuration reloaded')


# Global config instance
_config = None


def get_config(config_path: str = 'config.json') -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config
