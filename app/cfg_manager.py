"""
Configuration Management System

This module provides a flexible configuration management system that:
1. Reads non-sensitive configs from YAML files
2. Reads sensitive data from .env files
3. Merges configurations with environment-specific overrides
4. Provides dot notation access (Cfg.database.host)
5. Returns None for missing attributes instead of raising errors
"""

import os
import yaml
from typing import Any, Dict, Optional, Union
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


class NullConfigDict:
    """
    A null object that returns None for any attribute access.
    This allows for safe chaining of attribute access like Cfg.a.b.c.d
    even when intermediate keys don't exist.
    """
    
    def __getattr__(self, key: str) -> 'NullConfigDict':
        """Return another NullConfigDict for chaining."""
        return NullConfigDict()
    
    def __getitem__(self, key: str) -> 'NullConfigDict':
        """Return another NullConfigDict for dictionary-style access."""
        return NullConfigDict()
    
    def __str__(self) -> str:
        return "None"
    
    def __repr__(self) -> str:
        return "None"
    
    def __bool__(self) -> bool:
        return False
    
    def __eq__(self, other) -> bool:
        return other is None or isinstance(other, NullConfigDict)


class ConfigDict(dict):
    """
    A dictionary that supports dot notation access and returns None for missing keys.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Convert nested dictionaries to ConfigDict instances
        self._convert_nested_dicts()
    
    def _convert_nested_dicts(self):
        """Recursively convert nested dictionaries to ConfigDict instances."""
        for key, value in list(self.items()):
            if isinstance(value, dict) and not isinstance(value, ConfigDict):
                self[key] = ConfigDict(value)
    
    def __getattr__(self, key: str) -> Any:
        """
        Allow dot notation access to dictionary keys.
        Returns NullConfigDict if key doesn't exist instead of raising AttributeError.
        """
        try:
            value = self[key]
            return value
        except KeyError:
            return NullConfigDict()
    
    def __setattr__(self, key: str, value: Any) -> None:
        """Allow setting values using dot notation."""
        if isinstance(value, dict):
            value = ConfigDict(value)
        self[key] = value
    
    def __delattr__(self, key: str) -> None:
        """Allow deleting values using dot notation."""
        try:
            del self[key]
        except KeyError:
            pass  # Silently ignore missing keys
    
    def get_nested(self, path: str, default: Any = None) -> Any:
        """
        Get a nested value using dot notation path.
        
        Args:
            path: Dot-separated path (e.g., 'database.host')
            default: Default value if path doesn't exist
            
        Returns:
            Value at the path or default if not found
        """
        keys = path.split('.')
        current = self
        
        for key in keys:
            if isinstance(current, ConfigDict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def set_nested(self, path: str, value: Any) -> None:
        """
        Set a nested value using dot notation path.
        
        Args:
            path: Dot-separated path (e.g., 'database.host')
            value: Value to set
        """
        keys = path.split('.')
        current = self
        
        # Navigate to the parent of the final key
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], ConfigDict):
                current[key] = ConfigDict()
            current = current[key]
        
        # Set the final value
        if isinstance(value, dict):
            value = ConfigDict(value)
        current[keys[-1]] = value


class ConfigManager:
    """
    Configuration manager that loads and merges YAML configs with environment variables.
    """
    
    def __init__(self, config_dir: str = "cfg", env_file: str = ".env", environment: str = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing YAML config files
            env_file: Path to .env file
            environment: Environment name (development, production, testing)
        """
        self.config_dir = Path(config_dir)
        self.env_file = env_file
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self._config = ConfigDict()
        
        # Load configurations
        self._load_env_file()
        self._load_yaml_configs()
        self._merge_env_variables()
    
    def _load_env_file(self) -> None:
        """Load environment variables from .env file."""
        if os.path.exists(self.env_file):
            load_dotenv(self.env_file)
            logger.info(f"Loaded environment variables from {self.env_file}")
        else:
            logger.warning(f"Environment file {self.env_file} not found")
    
    def _load_yaml_configs(self) -> None:
        """Load and merge YAML configuration files."""
        # Load base configuration first
        base_config = self._load_yaml_file("base.yaml")
        if base_config:
            # Convert to ConfigDict and update
            base_config_dict = ConfigDict(base_config)
            self._config.update(base_config_dict)
        
        # Load environment-specific configuration
        env_config = self._load_yaml_file(f"{self.environment}.yaml")
        if env_config:
            self._merge_configs(self._config, env_config)
        
        logger.info(f"Loaded configuration for environment: {self.environment}")
    
    def _load_yaml_file(self, filename: str) -> Optional[Dict]:
        """Load a single YAML file."""
        file_path = self.config_dir / filename
        
        if not file_path.exists():
            if filename != "base.yaml":  # base.yaml is required
                logger.warning(f"Config file not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                logger.debug(f"Loaded config from {file_path}")
                return config or {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading config file {file_path}: {e}")
            return None
    
    def _merge_configs(self, base: ConfigDict, override: Dict) -> None:
        """
        Recursively merge configuration dictionaries.
        
        Args:
            base: Base configuration (modified in place)
            override: Override configuration
        """
        for key, value in override.items():
            if (key in base and 
                isinstance(base[key], (dict, ConfigDict)) and 
                isinstance(value, dict)):
                # Recursively merge nested dictionaries
                if not isinstance(base[key], ConfigDict):
                    base[key] = ConfigDict(base[key])
                self._merge_configs(base[key], value)
            else:
                # Override or add new key
                if isinstance(value, dict):
                    base[key] = ConfigDict(value)
                else:
                    base[key] = value
    
    def _merge_env_variables(self) -> None:
        """Merge sensitive data from environment variables."""
        env_mappings = {
            # Database configuration
            'DB_HOST': 'database.host',
            'DB_PORT': 'database.port',
            'DB_USER': 'database.user',
            'DB_PASSWORD': 'database.password',
            'DB_NAME': 'database.name',
            'DB_DRIVER': 'database.driver',
            
            # Redis configuration
            'REDIS_HOST': 'redis.host',
            'REDIS_PORT': 'redis.port',
            'REDIS_DB': 'redis.db',
            'REDIS_PASSWORD': 'redis.password',
            
            # JWT configuration
            'SECRET_KEY': 'jwt.secret_key',
            'ALGORITHM': 'jwt.algorithm',
            
            # Email configuration
            'SENDGRID_API_KEY': 'email.sendgrid_api_key',
            'FROM_EMAIL': 'email.from_email',
            'FROM_NAME': 'email.from_name',
            
            # Application configuration
            'DEBUG': 'app.debug',
            'APP_NAME': 'app.name',
            'VERSION': 'app.version',
            
            # CORS origins (special handling for list)
            'CORS_ORIGINS': 'cors.origins',
            
            # Security
            'CSRF_SECRET_KEY': 'security.csrf_secret_key',
            'OTP_EXPIRE_MINUTES': 'security.otp_expire_minutes',
            'PASSWORD_RESET_EXPIRE_MINUTES': 'security.password_reset_expire_minutes',
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Type conversion
                converted_value = self._convert_env_value(env_value, env_var)
                self._config.set_nested(config_path, converted_value)
        
        # Handle special cases
        self._handle_special_env_vars()
    
    def _convert_env_value(self, value: str, env_var: str) -> Union[str, int, bool, list]:
        """Convert environment variable string to appropriate type."""
        # Boolean conversion
        if env_var in ['DEBUG'] or value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        
        # Integer conversion
        if env_var in ['DB_PORT', 'REDIS_PORT', 'REDIS_DB', 'ACCESS_TOKEN_EXPIRE_MINUTES', 
                       'OTP_EXPIRE_MINUTES', 'PASSWORD_RESET_EXPIRE_MINUTES']:
            try:
                return int(value)
            except ValueError:
                logger.warning(f"Could not convert {env_var}={value} to integer")
                return value
        
        # List conversion (comma-separated)
        if env_var in ['CORS_ORIGINS']:
            return [origin.strip() for origin in value.split(',') if origin.strip()]
        
        return value
    
    def _handle_special_env_vars(self) -> None:
        """Handle special environment variable cases."""
        # Handle DATABASE_URL override
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            self._config.set_nested('database.url', database_url)
        
        # Handle REDIS_URL override
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            self._config.set_nested('redis.url', redis_url)
    
    @property
    def config(self) -> ConfigDict:
        """Get the merged configuration."""
        return self._config
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            path: Dot-separated path (e.g., 'database.host')
            default: Default value if path doesn't exist
            
        Returns:
            Configuration value or default
        """
        return self._config.get_nested(path, default)
    
    def set(self, path: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.
        
        Args:
            path: Dot-separated path (e.g., 'database.host')
            value: Value to set
        """
        self._config.set_nested(path, value)
    
    def reload(self) -> None:
        """Reload configuration from files."""
        self._config.clear()
        self._load_env_file()
        self._load_yaml_configs()
        self._merge_env_variables()
        logger.info("Configuration reloaded")
    
    def dump(self) -> Dict:
        """
        Return the entire configuration as a regular dictionary.
        Useful for debugging or serialization.
        """
        return dict(self._config)


# Global configuration instance
_config_manager = None


def get_config_manager(config_dir: str = "cfg", env_file: str = ".env", 
                      environment: str = None) -> ConfigManager:
    """
    Get or create the global configuration manager instance.
    
    Args:
        config_dir: Directory containing YAML config files
        env_file: Path to .env file
        environment: Environment name
        
    Returns:
        ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_dir, env_file, environment)
    return _config_manager


def init_config(config_dir: str = "cfg", env_file: str = ".env", 
               environment: str = None) -> ConfigDict:
    """
    Initialize and return the global configuration.
    
    Args:
        config_dir: Directory containing YAML config files
        env_file: Path to .env file
        environment: Environment name
        
    Returns:
        ConfigDict instance with dot notation access
    """
    manager = get_config_manager(config_dir, env_file, environment)
    return manager.config


# Convenience alias for the configuration
Cfg = None


def setup_config(config_dir: str = "cfg", env_file: str = ".env", 
                environment: str = None) -> ConfigDict:
    """
    Setup the global Cfg object.
    
    Args:
        config_dir: Directory containing YAML config files
        env_file: Path to .env file
        environment: Environment name
        
    Returns:
        ConfigDict instance
    """
    global Cfg
    Cfg = init_config(config_dir, env_file, environment)
    return Cfg 