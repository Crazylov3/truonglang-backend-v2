"""
Configuration module for Giao Duc Thang Long

This module provides a configuration system that:
1. Loads non-sensitive configs from YAML files (cfg/ directory)
2. Loads sensitive data from .env files
3. Provides backward compatibility with the old settings interface
4. Supports dot notation access (Cfg.database.host)
"""

from typing import List, Optional, Any
import os
from app.cfg_manager import setup_config, ConfigDict

# Initialize configuration
Cfg = setup_config()


class Settings:
    """
    Backward compatibility wrapper for the old Settings class.
    This allows existing code to continue working while using the new config system.
    """
    
    def __init__(self):
        self._cfg = Cfg
    
    # Database Configuration
    @property
    def database_url(self) -> str:
        """Build database URL from components or use override."""
        # Check for direct URL override first
        if self._cfg.database and self._cfg.database.url:
            return self._cfg.database.url
        
        # Build from components
        driver = self._cfg.database.driver or "postgresql+asyncpg"
        user = self._cfg.database.user or "learnify"
        password = self._cfg.database.password or "password"
        host = self._cfg.database.host or "localhost"
        port = self._cfg.database.port or 5432
        name = self._cfg.database.name or "learnify_db"
        
        return f"{driver}://{user}:{password}@{host}:{port}/{name}"
    
    @property
    def db_host(self) -> str:
        return self._cfg.database.host or "localhost"
    
    @property
    def db_port(self) -> int:
        return self._cfg.database.port or 5432
    
    @property
    def db_user(self) -> str:
        return self._cfg.database.user or "learnify"
    
    @property
    def db_password(self) -> str:
        return self._cfg.database.password or "password"
    
    @property
    def db_name(self) -> str:
        return self._cfg.database.name or "learnify_db"
    
    @property
    def db_driver(self) -> str:
        return self._cfg.database.driver or "postgresql+asyncpg"
    
    # Redis Configuration
    @property
    def redis_url(self) -> str:
        """Build Redis URL from components or use override."""
        # Check for direct URL override first
        if self._cfg.redis and self._cfg.redis.url:
            return self._cfg.redis.url
        
        # Build from components
        host = self._cfg.redis.host or "localhost"
        port = self._cfg.redis.port or 6379
        db = self._cfg.redis.db or 0
        password = self._cfg.redis.password
        
        if password:
            return f"redis://:{password}@{host}:{port}/{db}"
        else:
            return f"redis://{host}:{port}/{db}"
    
    @property
    def redis_host(self) -> str:
        return self._cfg.redis.host or "localhost"
    
    @property
    def redis_port(self) -> int:
        return self._cfg.redis.port or 6379
    
    @property
    def redis_db(self) -> int:
        return self._cfg.redis.db or 0
    
    @property
    def redis_password(self) -> Optional[str]:
        return self._cfg.redis.password
    
    # JWT Configuration
    @property
    def secret_key(self) -> str:
        return self._cfg.jwt.secret_key or "your-super-secret-key-here-change-in-production"
    
    @property
    def algorithm(self) -> str:
        return self._cfg.jwt.algorithm or "HS256"
    
    @property
    def access_token_expire_minutes(self) -> int:
        return self._cfg.jwt.access_token_expire_minutes or 30
    
    # Email Configuration
    @property
    def sendgrid_api_key(self) -> str:
        return self._cfg.email.sendgrid_api_key or ""
    
    @property
    def from_email(self) -> str:
        return self._cfg.email.from_email or "noreply@learnify.com"
    
    @property
    def from_name(self) -> str:
        return self._cfg.email.from_name or "Giao Duc Thang Long"
    
    # Application Configuration
    @property
    def debug(self) -> bool:
        return self._cfg.app.debug or False
    
    @property
    def sql_debug(self) -> bool:
        """Control SQL query logging separately from main debug setting."""
        return self._cfg.database.get('sql_debug', False) if self._cfg.database else False
    
    @property
    def app_name(self) -> str:
        return self._cfg.app.name or "Giao Duc Thang Long"
    
    @property
    def version(self) -> str:
        return self._cfg.app.version or "1.0.0"
    
    @property
    def cors_origins(self) -> List[str]:
        if self._cfg.cors and self._cfg.cors.origins:
            return self._cfg.cors.origins
        return ["http://localhost:3000", "http://localhost:8080"]
    
    # Security Configuration
    @property
    def csrf_secret_key(self) -> str:
        return self._cfg.security.csrf_secret_key or "your-csrf-secret-key-here"
    
    @property
    def otp_expire_minutes(self) -> int:
        return self._cfg.security.otp_expire_minutes or 10
    
    @property
    def password_reset_expire_minutes(self) -> int:
        return self._cfg.security.password_reset_expire_minutes or 30
    
    @property
    def csrf_token_expire_minutes(self) -> int:
        return self._cfg.security.csrf_token_expire_minutes or 60
    
    @property
    def allowed_hosts(self) -> List[str]:
        if self._cfg.security and self._cfg.security.allowed_hosts:
            return self._cfg.security.allowed_hosts
        return ["*"]  # Default to allow all hosts
    
    def __getattr__(self, name: str) -> Any:
        try:
            return super().__getattr__(name)
        except AttributeError:
            return self._cfg.get(name)
        
    def __getitem__(self, key: str) -> Any:
        return self._cfg.get(key)
    


# Global settings instance for backward compatibility
settings = Settings()


# Export both the new Cfg object and legacy settings for compatibility
__all__ = ['Cfg', 'settings', 'Settings'] 