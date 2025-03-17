"""
Example implementation of the configuration provider hook for multi-tenant deployments.

This module provides examples of how to implement configuration providers to
customize agent behavior and system settings based on user or tenant-specific needs.
"""

from typing import Dict, Any, Optional
import json
import os
import yaml


class ConfigurationProvider:
    """Base protocol for configuration providers"""
    
    def get_configuration(self, scope: str) -> Dict[str, Any]:
        """Get configuration for a specific scope
        
        Args:
            scope: The scope to get configuration for (e.g., 'agent', 'memory', 'workflow')
            
        Returns:
            Dictionary containing configuration for the specified scope
        """
        raise NotImplementedError("Subclasses must implement get_configuration()")


class FileConfigurationProvider(ConfigurationProvider):
    """Configuration provider that loads from a JSON or YAML file"""
    
    def __init__(self, config_file: str):
        """Initialize a file-based configuration provider
        
        Args:
            config_file: Path to the configuration file
        """
        self.config_file = config_file
        self.config_data = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file
        
        Returns:
            Dictionary containing configuration data
        """
        if not os.path.exists(self.config_file):
            return {}
            
        if self.config_file.endswith('.json'):
            with open(self.config_file, 'r') as f:
                return json.load(f)
                
        elif self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f)
                
        else:
            raise ValueError(f"Unsupported config file format: {self.config_file}")
            
    def get_configuration(self, scope: str) -> Dict[str, Any]:
        """Get configuration for a specific scope
        
        Args:
            scope: The scope to get configuration for
            
        Returns:
            Dictionary containing configuration for the specified scope
        """
        return self.config_data.get(scope, {})


class UserConfigurationProvider(ConfigurationProvider):
    """Configuration provider that loads user-specific configurations"""
    
    def __init__(self, user_id: str, config_service=None):
        """Initialize a user-specific configuration provider
        
        Args:
            user_id: The ID of the user
            config_service: Optional service for retrieving configuration data
        """
        self.user_id = user_id
        self.config_service = config_service
        
        # Default configurations if no service is provided
        self.default_configs = {
            'agent': {
                'model': 'gpt-3.5-turbo',
                'temperature': 0.7,
                'max_tokens': 1000,
                'system_prompt': 'You are a helpful assistant.'
            },
            'memory': {
                'ttl': 3600,  # Time to live in seconds
                'max_size': 10000
            },
            'workflow': {
                'max_tasks': 10,
                'timeout': 300  # Timeout in seconds
            }
        }
        
    def get_configuration(self, scope: str) -> Dict[str, Any]:
        """Get user-specific configuration for a scope
        
        Args:
            scope: The scope to get configuration for
            
        Returns:
            Dictionary containing configuration for the specified scope
        """
        # If we have a config service, fetch from it
        if self.config_service:
            return self.config_service.get_user_config(self.user_id, scope)
            
        # Otherwise return defaults
        return self.default_configs.get(scope, {})
        
    def update_configuration(self, scope: str, config: Dict[str, Any]) -> None:
        """Update configuration for a scope
        
        Args:
            scope: The scope to update configuration for
            config: The configuration data to set
        """
        if self.config_service:
            self.config_service.update_user_config(self.user_id, scope, config)
        else:
            self.default_configs[scope] = config


class OrganizationConfigurationProvider(ConfigurationProvider):
    """Configuration provider for organization-specific configurations"""
    
    def __init__(self, org_id: str, config_service=None):
        """Initialize an organization-specific configuration provider
        
        Args:
            org_id: The ID of the organization
            config_service: Optional service for retrieving configuration data
        """
        self.org_id = org_id
        self.config_service = config_service
        
        # Default configurations if no service is provided
        self.default_configs = {
            'agent': {
                'model': 'gpt-4',
                'temperature': 0.5,
                'max_tokens': 2000
            },
            'memory': {
                'ttl': 86400,  # 24 hours
                'max_size': 100000
            },
            'workflow': {
                'max_tasks': 20,
                'timeout': 600
            }
        }
        
    def get_configuration(self, scope: str) -> Dict[str, Any]:
        """Get organization-specific configuration for a scope
        
        Args:
            scope: The scope to get configuration for
            
        Returns:
            Dictionary containing configuration for the specified scope
        """
        # If we have a config service, fetch from it
        if self.config_service:
            return self.config_service.get_org_config(self.org_id, scope)
            
        # Otherwise return defaults
        return self.default_configs.get(scope, {})


class HierarchicalConfigurationProvider(ConfigurationProvider):
    """Configuration provider that combines multiple providers with precedence"""
    
    def __init__(self, providers: Dict[str, ConfigurationProvider], order: Optional[list] = None):
        """Initialize a hierarchical configuration provider
        
        Args:
            providers: Dictionary mapping provider names to providers
            order: Optional list specifying the precedence order of providers
                  (first provider has highest precedence)
        """
        self.providers = providers
        self.order = order or list(providers.keys())
        
    def get_configuration(self, scope: str) -> Dict[str, Any]:
        """Get configuration for a scope by combining multiple providers
        
        Args:
            scope: The scope to get configuration for
            
        Returns:
            Dictionary containing merged configuration for the specified scope
        """
        # Start with an empty configuration
        merged_config = {}
        
        # Apply configurations in reverse order (lowest precedence first)
        for provider_name in reversed(self.order):
            provider = self.providers.get(provider_name)
            if provider:
                provider_config = provider.get_configuration(scope)
                merged_config.update(provider_config)
                
        return merged_config


# Example usage
def example_usage():
    """Demonstrate how to use configuration providers"""
    from src.orcs.agent.infrastructure import PlannerAgent
    
    # Create a file-based configuration provider
    file_config = FileConfigurationProvider('config.json')
    
    # Create a user-specific configuration provider
    user_config = UserConfigurationProvider('user123')
    
    # Create an organization-specific configuration provider
    org_config = OrganizationConfigurationProvider('org456')
    
    # Create a hierarchical configuration provider
    # Order: user > org > file (user settings override org settings, which override file settings)
    hierarchical_config = HierarchicalConfigurationProvider(
        providers={
            'user': user_config,
            'org': org_config,
            'file': file_config
        },
        order=['user', 'org', 'file']
    )
    
    # Create a planner agent with the hierarchical configuration
    planner = PlannerAgent(
        model="gpt-4",
        config_provider=hierarchical_config
    )
    
    # The agent will use:
    # 1. User-specific configurations where available
    # 2. Organization-specific configurations where user configs aren't specified
    # 3. File-based configurations where neither user nor org configs are specified
    # 4. Default values where no configurations are specified
    
    # For example, if:
    # - user_config specifies temperature=0.8
    # - org_config specifies temperature=0.5 and max_tokens=2000
    # - file_config specifies model="gpt-4-turbo"
    #
    # The agent will use:
    # - temperature=0.8 (from user_config)
    # - max_tokens=2000 (from org_config)
    # - model="gpt-4-turbo" (from file_config, but this might be overridden by the explicit model="gpt-4" in initialization)


 