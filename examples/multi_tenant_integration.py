#!/usr/bin/env python3
"""
ORCS Multi-Tenant Integration Example

This script demonstrates how to use all the extension hooks together
to build a multi-tenant integration of ORCS.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from src.orcs.memory.system import MemorySystem
from src.orcs.workflow.models import Workflow
from src.orcs.workflow.controller import WorkflowController
from src.orcs.workflow.orchestrator import WorkflowOrchestrator
from src.orcs.agent.infrastructure import PlannerAgent

# Import example extension hooks
from examples.extension_hooks.isolation_provider import UserIsolationProvider, OrganizationIsolationProvider
from examples.extension_hooks.context_provider import UserContextProvider, OrganizationContextProvider, CompoundContextProvider
from examples.extension_hooks.authorization_hook import UserPermissionChecker
from examples.extension_hooks.resource_manager import UserResourceManager
from examples.extension_hooks.telemetry_collector import UserTelemetryCollector
from examples.extension_hooks.config_provider import UserConfigurationProvider, OrganizationConfigurationProvider, HierarchicalConfigurationProvider


class MultiTenantORCS:
    """A multi-tenant wrapper for ORCS"""
    
    def __init__(self, services=None):
        """Initialize a multi-tenant ORCS instance
        
        Args:
            services: Optional dictionary of external services to use
        """
        # External services (databases, etc.)
        self.services = services or {}
        
        # Common agent registry
        self.agent_registry = {}
        
        # Set up logging
        self.logger = logging.getLogger("orcs.multi_tenant")
        
    async def get_for_user(self, user_id: str, org_id: Optional[str] = None) -> Dict[str, Any]:
        """Get ORCS components for a specific user
        
        Args:
            user_id: The ID of the user
            org_id: Optional organization ID
            
        Returns:
            Dictionary containing ORCS components for the user
        """
        # Set up isolation provider
        if org_id:
            # Use compound isolation if user belongs to an organization
            isolation_provider = OrganizationIsolationProvider(org_id)
        else:
            # Otherwise use user isolation
            isolation_provider = UserIsolationProvider(user_id)
            
        # Create isolated memory system
        memory = MemorySystem(isolation_provider=isolation_provider)
        
        # Set up context providers
        context_providers = [UserContextProvider(user_id)]
        if org_id:
            context_providers.append(OrganizationContextProvider(org_id))
            
        context_provider = CompoundContextProvider(context_providers)
        
        # Set up permission checker
        permission_checker = UserPermissionChecker(user_id)
        
        # Set up resource manager
        resource_manager = UserResourceManager(user_id)
        
        # Set up telemetry collector
        telemetry_collector = UserTelemetryCollector(user_id)
        
        # Set up configuration provider
        config_providers = {
            'user': UserConfigurationProvider(user_id)
        }
        
        if org_id:
            config_providers['org'] = OrganizationConfigurationProvider(org_id)
            
        config_provider = HierarchicalConfigurationProvider(
            providers=config_providers,
            order=['user', 'org', 'default']
        )
        
        # Create planner agent with configuration
        planner = PlannerAgent(
            model="gpt-4",
            config_provider=config_provider
        )
        
        # Create workflow controller
        controller = WorkflowController(
            planner_agent=planner,
            memory_system=memory,
            permission_checker=permission_checker
        )
        
        # Create workflow orchestrator
        orchestrator = WorkflowOrchestrator(
            memory_system=memory,
            agent_registry=self.agent_registry,
            resource_manager=resource_manager,
            telemetry_collector=telemetry_collector
        )
        
        # Return all components
        return {
            'memory': memory,
            'controller': controller,
            'orchestrator': orchestrator,
            'context_provider': context_provider
        }
        
    async def create_workflow_for_user(self, user_id: str, query: str, org_id: Optional[str] = None) -> Dict[str, Any]:
        """Create and execute a workflow for a specific user
        
        Args:
            user_id: The ID of the user
            query: The query to create a workflow for
            org_id: Optional organization ID
            
        Returns:
            Dictionary containing workflow result information
        """
        # Get ORCS components for the user
        components = await self.get_for_user(user_id, org_id)
        
        # Create a workflow
        workflow_id = await components['controller'].create_workflow(
            query=query,
            context_provider=components['context_provider']
        )
        
        # Get the created workflow
        workflow = await components['controller'].get_workflow(workflow_id)
        
        # Log workflow creation
        self.logger.info(f"Created workflow {workflow_id} for user {user_id}")
        
        # Execute the workflow
        result = await components['orchestrator'].execute(workflow)
        
        # Log workflow completion
        self.logger.info(f"Executed workflow {workflow_id} for user {user_id}: {result['status']}")
        
        return {
            'workflow_id': workflow_id,
            'status': result['status'],
            'results': result['results']
        }


async def main():
    """Run the multi-tenant example"""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create multi-tenant ORCS
    multi_tenant_orcs = MultiTenantORCS()
    
    # Create workflows for different users
    user1_result = await multi_tenant_orcs.create_workflow_for_user(
        user_id="user123",
        query="Create a report about renewable energy trends"
    )
    
    user2_result = await multi_tenant_orcs.create_workflow_for_user(
        user_id="user456",
        query="Develop a marketing strategy for a new product",
        org_id="org789"
    )
    
    # Output results
    print(f"User 1 Workflow Status: {user1_result['status']}")
    print(f"User 2 Workflow Status: {user2_result['status']}")


if __name__ == "__main__":
    asyncio.run(main()) 