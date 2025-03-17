"""
Example implementation of the context injection hook for multi-tenant deployments.

This module provides examples of how to implement context providers to inject
user-specific or tenant-specific context into workflows.
"""

from typing import Dict, Any, List, Optional
import asyncio


class ContextProvider:
    """Base protocol for context providers"""
    
    async def get_context(self) -> Dict[str, Any]:
        """Get the context to inject into a workflow
        
        Returns:
            A dictionary containing the context data
        """
        raise NotImplementedError("Subclasses must implement get_context()")


class UserContextProvider(ContextProvider):
    """Provides user-specific context for workflows"""
    
    def __init__(self, user_id: str, user_db=None):
        """Initialize a user context provider
        
        Args:
            user_id: The ID of the user
            user_db: Optional database for retrieving user data
        """
        self.user_id = user_id
        self.user_db = user_db
        
    async def get_context(self) -> Dict[str, Any]:
        """Get user-specific context for workflow execution
        
        Returns:
            Dictionary containing user-specific context data
        """
        # If we have a user database, fetch data from it
        if self.user_db:
            user = await self.user_db.get_user(self.user_id)
            return {
                'preferences': user.preferences,
                'history': user.previous_queries,
                'permissions': user.permission_levels
            }
        
        # Otherwise, return a simple example context
        return {
            'user_id': self.user_id,
            'preferences': {
                'language': 'en',
                'timezone': 'UTC',
                'theme': 'light'
            }
        }


class OrganizationContextProvider(ContextProvider):
    """Provides organization-specific context for workflows"""
    
    def __init__(self, org_id: str, org_db=None):
        """Initialize an organization context provider
        
        Args:
            org_id: The ID of the organization
            org_db: Optional database for retrieving organization data
        """
        self.org_id = org_id
        self.org_db = org_db
        
    async def get_context(self) -> Dict[str, Any]:
        """Get organization-specific context for workflow execution
        
        Returns:
            Dictionary containing organization-specific context data
        """
        # If we have an organization database, fetch data from it
        if self.org_db:
            org = await self.org_db.get_organization(self.org_id)
            return {
                'organization_name': org.name,
                'domain': org.domain,
                'policies': org.policies
            }
        
        # Otherwise, return a simple example context
        return {
            'organization_id': self.org_id,
            'domain': f"{self.org_id}.example.com",
            'policies': {
                'security_level': 'standard',
                'data_retention': '30 days'
            }
        }


class CompoundContextProvider(ContextProvider):
    """Combines multiple context providers into one"""
    
    def __init__(self, providers: List[ContextProvider]):
        """Initialize a compound context provider
        
        Args:
            providers: List of context providers to combine
        """
        self.providers = providers
        
    async def get_context(self) -> Dict[str, Any]:
        """Get combined context from all providers
        
        Returns:
            Dictionary containing combined context data
        """
        # Gather context from all providers
        contexts = await asyncio.gather(
            *[provider.get_context() for provider in self.providers]
        )
        
        # Combine the contexts
        combined_context = {}
        for context in contexts:
            combined_context.update(context)
            
        return combined_context


class ProjectContextProvider(ContextProvider):
    """Provides project-specific context for workflows"""
    
    def __init__(self, project_id: str, project_db=None):
        """Initialize a project context provider
        
        Args:
            project_id: The ID of the project
            project_db: Optional database for retrieving project data
        """
        self.project_id = project_id
        self.project_db = project_db
        
    async def get_context(self) -> Dict[str, Any]:
        """Get project-specific context for workflow execution
        
        Returns:
            Dictionary containing project-specific context data
        """
        # If we have a project database, fetch data from it
        if self.project_db:
            project = await self.project_db.get_project(self.project_id)
            return {
                'project_name': project.name,
                'description': project.description,
                'resources': project.resources,
                'team_members': project.team_members
            }
        
        # Otherwise, return a simple example context
        return {
            'project_id': self.project_id,
            'description': f"Project {self.project_id}",
            'resources': ['resource1', 'resource2']
        }


# Example usage
async def example_usage():
    """Demonstrate how to use context providers"""
    from src.orcs.workflow.controller import WorkflowController
    from src.orcs.memory.system import MemorySystem
    from src.orcs.agent.infrastructure import PlannerAgent
    
    # Create a workflow controller with various context providers
    
    # Basic memory system and planner
    memory = MemorySystem()
    planner = PlannerAgent(model="gpt-4")
    
    # Create the controller
    controller = WorkflowController(
        planner_agent=planner,
        memory_system=memory
    )
    
    # Create different context providers
    user_provider = UserContextProvider("user123")
    org_provider = OrganizationContextProvider("org456")
    
    # Compound provider combining user and organization context
    compound_provider = CompoundContextProvider([
        user_provider,
        org_provider
    ])
    
    # Create workflows with different context providers
    user_workflow_id = await controller.create_workflow(
        query="Create a report",
        context_provider=user_provider
    )
    
    org_workflow_id = await controller.create_workflow(
        query="Create a report",
        context_provider=org_provider
    )
    
    compound_workflow_id = await controller.create_workflow(
        query="Create a report",
        context_provider=compound_provider
    )
    
    # The workflows now have different contexts injected:
    # - User workflow has user preferences
    # - Organization workflow has organization policies
    # - Compound workflow has both
    
    # These contexts can influence how the planner creates tasks
    # and how agents execute those tasks


if __name__ == "__main__":
    asyncio.run(example_usage()) 