"""
Example implementation of the data isolation hook for multi-tenant deployments.

This module provides examples of how to implement isolation providers to keep
data separate between different users or tenants in a multi-tenant deployment.
"""

from typing import Dict, Any


class IsolationProvider:
    """Base protocol for isolation providers"""
    
    def get_isolation_prefix(self) -> str:
        """Get the isolation prefix for data isolation
        
        Returns:
            A string prefix to use for data isolation
        """
        raise NotImplementedError("Subclasses must implement get_isolation_prefix()")


class UserIsolationProvider(IsolationProvider):
    """Provides isolation for user-specific data"""
    
    def __init__(self, user_id: str):
        """Initialize a user isolation provider
        
        Args:
            user_id: The ID of the user
        """
        self.user_id = user_id
        
    def get_isolation_prefix(self) -> str:
        """Get the isolation prefix for this user
        
        Returns:
            A string prefix in the format "user:{user_id}"
        """
        return f"user:{self.user_id}"


class OrganizationIsolationProvider(IsolationProvider):
    """Provides isolation for organization-specific data"""
    
    def __init__(self, org_id: str):
        """Initialize an organization isolation provider
        
        Args:
            org_id: The ID of the organization
        """
        self.org_id = org_id
        
    def get_isolation_prefix(self) -> str:
        """Get the isolation prefix for this organization
        
        Returns:
            A string prefix in the format "org:{org_id}"
        """
        return f"org:{self.org_id}"


class ProjectIsolationProvider(IsolationProvider):
    """Provides isolation for project-specific data"""
    
    def __init__(self, project_id: str):
        """Initialize a project isolation provider
        
        Args:
            project_id: The ID of the project
        """
        self.project_id = project_id
        
    def get_isolation_prefix(self) -> str:
        """Get the isolation prefix for this project
        
        Returns:
            A string prefix in the format "project:{project_id}"
        """
        return f"project:{self.project_id}"


class CompoundIsolationProvider(IsolationProvider):
    """Provides isolation with multiple layers (e.g., org and user)"""
    
    def __init__(self, org_id: str, user_id: str):
        """Initialize a compound isolation provider
        
        Args:
            org_id: The ID of the organization
            user_id: The ID of the user
        """
        self.org_id = org_id
        self.user_id = user_id
        
    def get_isolation_prefix(self) -> str:
        """Get the isolation prefix with multiple layers
        
        Returns:
            A string prefix in the format "org:{org_id}:user:{user_id}"
        """
        return f"org:{self.org_id}:user:{self.user_id}"


# Example usage
def example_usage():
    """Demonstrate how to use isolation providers"""
    from src.orcs.memory.system import MemorySystem
    
    # Create memory systems with different isolation providers
    
    # User isolation
    user_isolation = UserIsolationProvider("user123")
    user_memory = MemorySystem(isolation_provider=user_isolation)
    
    # Organization isolation
    org_isolation = OrganizationIsolationProvider("org456")
    org_memory = MemorySystem(isolation_provider=org_isolation)
    
    # Compound isolation
    compound_isolation = CompoundIsolationProvider("org456", "user123")
    compound_memory = MemorySystem(isolation_provider=compound_isolation)
    
    # Store the same key in each memory system
    user_memory.store("test_key", "user value")
    org_memory.store("test_key", "org value")
    compound_memory.store("test_key", "compound value")
    
    # Internally, these are stored with different prefixes:
    # - "user:user123:test_key" = "user value"
    # - "org:org456:test_key" = "org value"
    # - "org:org456:user:user123:test_key" = "compound value"
    
    # But clients access them using the same simple key
    print(user_memory.retrieve("test_key", "global"))  # "user value"
    print(org_memory.retrieve("test_key", "global"))  # "org value"
    print(compound_memory.retrieve("test_key", "global"))  # "compound value"


if __name__ == "__main__":
    example_usage() 