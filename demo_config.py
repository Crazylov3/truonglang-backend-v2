#!/usr/bin/env python3
"""
Configuration System Demonstration

This script demonstrates the new configuration management system that:
1. Loads non-sensitive configs from YAML files
2. Loads sensitive data from environment variables
3. Provides dot notation access (Cfg.database.host)
4. Returns None for missing attributes instead of errors
5. Supports environment-specific configurations
"""

import os
from app.config import Cfg, settings

def demo_basic_access():
    """Demonstrate basic configuration access."""
    print("=== Basic Configuration Access ===")
    print(f"App name: {Cfg.app.name}")
    print(f"App version: {Cfg.app.version}")
    print(f"Database driver: {Cfg.database.driver}")
    print(f"Database port: {Cfg.database.port}")
    print(f"Redis port: {Cfg.redis.port}")
    print(f"JWT algorithm: {Cfg.jwt.algorithm}")
    print()


def demo_safe_access():
    """Demonstrate safe attribute access (returns None for missing keys)."""
    print("=== Safe Attribute Access ===")
    print(f"Non-existent top-level key: {Cfg.nonexistent}")
    print(f"Non-existent nested key: {Cfg.database.nonexistent}")
    print(f"Non-existent deep nested: {Cfg.app.some.deep.key}")
    print(f"Boolean check (should be False): {bool(Cfg.nonexistent.deep.nested)}")
    print(f"Equality check with None: {Cfg.nonexistent == None}")
    print()


def demo_environment_override():
    """Demonstrate environment variable overrides."""
    print("=== Environment Variable Overrides ===")
    print("Original values:")
    print(f"  Database host: {Cfg.database.host}")
    print(f"  Secret key: {Cfg.jwt.secret_key}")
    
    # Temporarily set environment variables
    os.environ['DB_HOST'] = 'custom-host'
    os.environ['SECRET_KEY'] = 'custom-secret-key'
    
    # Reload configuration
    from app.cfg_manager import get_config_manager
    manager = get_config_manager()
    manager.reload()
    
    print("\nAfter setting environment variables:")
    print(f"  Database host: {Cfg.database.host}")
    print(f"  Secret key: {Cfg.jwt.secret_key}")
    
    # Clean up
    del os.environ['DB_HOST']
    del os.environ['SECRET_KEY']
    manager.reload()
    print()


def demo_backward_compatibility():
    """Demonstrate backward compatibility with old Settings interface."""
    print("=== Backward Compatibility ===")
    print("Using old Settings interface:")
    print(f"  settings.app_name: {settings.app_name}")
    print(f"  settings.database_url: {settings.database_url}")
    print(f"  settings.redis_url: {settings.redis_url}")
    print(f"  settings.debug: {settings.debug}")
    print()


def demo_nested_access():
    """Demonstrate nested configuration access."""
    print("=== Nested Configuration Access ===")
    print(f"CORS origins: {Cfg.cors.origins}")
    print(f"File upload max size: {Cfg.file_upload.max_size_mb}MB")
    print(f"Allowed file types: {Cfg.file_upload.allowed_types}")
    print(f"Security settings:")
    print(f"  OTP expire minutes: {Cfg.security.otp_expire_minutes}")
    print(f"  Max login attempts: {Cfg.security.max_login_attempts}")
    print(f"  Min password length: {Cfg.security.min_password_length}")
    print()


def demo_environment_specific():
    """Demonstrate environment-specific configuration."""
    print("=== Environment-Specific Configuration ===")
    
    current_env = os.environ.get('ENVIRONMENT', 'development')
    print(f"Current environment: {current_env}")
    print(f"Debug mode: {Cfg.app.debug}")
    print(f"Database host: {Cfg.database.host}")
    print(f"Rate limiting enabled: {Cfg.rate_limiting.enabled}")
    
    if Cfg.rate_limiting.enabled:
        print(f"Rate limit: {Cfg.rate_limiting.requests_per_minute} requests/minute")
    
    print()


def demo_config_paths():
    """Demonstrate different ways to access configuration."""
    print("=== Different Access Methods ===")
    
    # Direct attribute access
    print(f"Direct access: {Cfg.database.host}")
    
    # Using get_nested method
    print(f"Using get_nested: {Cfg.get_nested('database.host')}")
    
    # Using get_nested with default
    print(f"With default: {Cfg.get_nested('database.nonexistent', 'default-value')}")
    
    # Manager get method
    from app.cfg_manager import get_config_manager
    manager = get_config_manager()
    print(f"Manager get: {manager.get('database.host')}")
    
    print()


def main():
    """Run all configuration demonstrations."""
    print("🚀 Learnify LMS Configuration System Demo")
    print("=" * 50)
    print()
    
    demo_basic_access()
    demo_safe_access()
    demo_environment_override()
    demo_backward_compatibility()
    demo_nested_access()
    demo_environment_specific()
    demo_config_paths()
    
    print("✅ Configuration system working correctly!")
    print()
    print("💡 Tips:")
    print("- Use Cfg.section.key for new code")
    print("- Use settings.property for legacy compatibility")
    print("- Store secrets in .env files")
    print("- Store non-sensitive configs in cfg/*.yaml files")
    print("- Set ENVIRONMENT variable to load different configs")


if __name__ == "__main__":
    main() 