"""
Example implementation of the authorization hook for multi-tenant deployments.

This module provides examples of how to implement permission checkers to 
control access to workflows and other resources in a multi-tenant deployment.
"""

from typing import Dict, Any, List, Optional, Set
import asyncio


class PermissionChecker:
    """Base protocol for permission checking"""
    
    def check_permission(self, operation: str, resource_id: str) -> bool:
        """Check if an operation is permitted on a resource
        
        Args:
            operation: The operation to check (e.g., 'read', 'write', 'execute')
            resource_id: The ID of the resource to check permissions for
            
        Returns:
            True if the operation is permitted, False otherwise
        """
        raise NotImplementedError("Subclasses must implement check_permission()")


class SimplePermissionChecker(PermissionChecker):
    """Simple permission checker with hardcoded permissions"""
    
    def __init__(self, permissions: Dict[str, List[str]]):
        """Initialize a simple permission checker
        
        Args:
            permissions: Dictionary mapping resource IDs to allowed operations
                        e.g., {'workflow123': ['read', 'execute']}
        """
        self.permissions = permissions
        
    def check_permission(self, operation: str, resource_id: str) -> bool:
        """Check if an operation is permitted on a resource
        
        Args:
            operation: The operation to check
            resource_id: The ID of the resource
            
        Returns:
            True if the operation is permitted, False otherwise
        """
        if resource_id not in self.permissions:
            return False
            
        return operation in self.permissions[resource_id]


class UserPermissionChecker(PermissionChecker):
    """Permission checker based on user roles and permissions"""
    
    def __init__(self, user_id: str, permission_service=None):
        """Initialize a user permission checker
        
        Args:
            user_id: The ID of the user
            permission_service: Optional service for checking permissions
        """
        self.user_id = user_id
        self.permission_service = permission_service
        
        # Example role-based permissions (used if no permission_service is provided)
        self.role = "user"  # Could be "admin", "user", "guest", etc.
        self.owned_resources = set()  # Resources owned by this user
        
    def check_permission(self, operation: str, resource_id: str) -> bool:
        """Check if the user has permission for an operation
        
        Args:
            operation: The operation to check
            resource_id: The ID of the resource
            
        Returns:
            True if the operation is permitted, False otherwise
        """
        # If we have a permission service, use it
        if self.permission_service:
            return self.permission_service.has_permission(
                self.user_id, operation, resource_id
            )
        
        # Otherwise, use our simple role-based logic
        
        # Admins can do anything
        if self.role == "admin":
            return True
            
        # Users can read any resource but only write/execute their own
        if self.role == "user":
            if operation == "read" or operation == "list":
                return True
            else:  # write, execute, delete, etc.
                return resource_id in self.owned_resources
                
        # Guests can only read
        if self.role == "guest":
            return operation == "read" or operation == "list"
            
        # Default deny
        return False
        
    def add_owned_resource(self, resource_id: str) -> None:
        """Add a resource to the user's owned resources
        
        Args:
            resource_id: The ID of the resource to add
        """
        self.owned_resources.add(resource_id)
        
    def set_role(self, role: str) -> None:
        """Set the user's role
        
        Args:
            role: The role to set
        """
        self.role = role


class OrganizationPermissionChecker(PermissionChecker):
    """Permission checker that checks organization-level permissions"""
    
    def __init__(self, org_id: str, user_id: str, permission_service=None):
        """Initialize an organization permission checker
        
        Args:
            org_id: The ID of the organization
            user_id: The ID of the user
            permission_service: Optional service for checking permissions
        """
        self.org_id = org_id
        self.user_id = user_id
        self.permission_service = permission_service
        
        # Example organization roles (used if no permission_service is provided)
        self.user_role = "member"  # Could be "owner", "admin", "member", "viewer", etc.
        self.org_resources = set()  # Resources belonging to this organization
        
    def check_permission(self, operation: str, resource_id: str) -> bool:
        """Check if the user has permission for an operation in this organization
        
        Args:
            operation: The operation to check
            resource_id: The ID of the resource
            
        Returns:
            True if the operation is permitted, False otherwise
        """
        # If we have a permission service, use it
        if self.permission_service:
            return self.permission_service.has_org_permission(
                self.org_id, self.user_id, operation, resource_id
            )
        
        # Otherwise, use our simple role-based logic
        
        # First check if the resource belongs to this organization
        if resource_id not in self.org_resources:
            return False
            
        # Check based on role
        if self.user_role == "owner" or self.user_role == "admin":
            return True
            
        if self.user_role == "member":
            return operation in ["read", "list", "execute"]
            
        if self.user_role == "viewer":
            return operation in ["read", "list"]
            
        # Default deny
        return False
        
    def add_org_resource(self, resource_id: str) -> None:
        """Add a resource to the organization's resources
        
        Args:
            resource_id: The ID of the resource to add
        """
        self.org_resources.add(resource_id)
        
    def set_user_role(self, role: str) -> None:
        """Set the user's role in this organization
        
        Args:
            role: The role to set
        """
        self.user_role = role


# Example usage
def example_usage():
    """Demonstrate how to use permission checkers"""
    from orcs.workflow.controller import WorkflowController
    from orcs.memory.system import MemorySystem
    from orcs.agent.infrastructure import PlannerAgent
    
    # Create a workflow controller with permission checking
    
    # Basic memory system and planner
    memory = MemorySystem()
    planner = PlannerAgent(model="gpt-4")
    
    # Create a simple permission checker
    simple_checker = SimplePermissionChecker({
        'workflow1': ['read', 'execute'],
        'workflow2': ['read']
    })
    
    # Create the controller with the permission checker
    controller = WorkflowController(
        planner_agent=planner,
        memory_system=memory,
        permission_checker=simple_checker
    )
    
    # This would allow reading workflow1
    try:
        workflow = controller.get_workflow('workflow1')
        print("Successfully read workflow1")
    except PermissionError:
        print("Permission denied to read workflow1")
    
    # This would allow executing workflow1
    try:
        controller.execute_workflow('workflow1')
        print("Successfully executed workflow1")
    except PermissionError:
        print("Permission denied to execute workflow1")
    
    # This would allow reading workflow2
    try:
        workflow = controller.get_workflow('workflow2')
        print("Successfully read workflow2")
    except PermissionError:
        print("Permission denied to read workflow2")
    
    # This would deny executing workflow2
    try:
        controller.execute_workflow('workflow2')
        print("Successfully executed workflow2")
    except PermissionError:
        print("Permission denied to execute workflow2")
    
    # Create a user permission checker
    user_checker = UserPermissionChecker('user123')
    user_checker.set_role('user')
    user_checker.add_owned_resource('workflow3')
    
    # Update the controller to use the user permission checker
    controller.permission_checker = user_checker
    
    # This would allow reading any workflow
    try:
        workflow = controller.get_workflow('workflow4')
        print("Successfully read workflow4")
    except PermissionError:
        print("Permission denied to read workflow4")
    
    # This would allow executing workflow3 (owned by user)
    try:
        controller.execute_workflow('workflow3')
        print("Successfully executed workflow3")
    except PermissionError:
        print("Permission denied to execute workflow3")
    
    # This would deny executing workflow4 (not owned by user)
    try:
        controller.execute_workflow('workflow4')
        print("Successfully executed workflow4")
    except PermissionError:
        print("Permission denied to execute workflow4")


if __name__ == "__main__":
    example_usage() 