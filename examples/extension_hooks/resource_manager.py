"""
Example implementation of the resource management hook for multi-tenant deployments.

This module provides examples of how to implement resource managers to allocate
and manage resources for workflows in a multi-tenant deployment.
"""

from typing import Dict, Any, List, Optional
import asyncio
import time


class ResourceManager:
    """Base protocol for resource management"""
    
    async def allocate_resources(self, workflow_id: str, requirements: Dict[str, Any]) -> bool:
        """Allocate resources for a workflow
        
        Args:
            workflow_id: The ID of the workflow requesting resources
            requirements: Dictionary of resource requirements
            
        Returns:
            True if resources were successfully allocated, False otherwise
        """
        raise NotImplementedError("Subclasses must implement allocate_resources()")
        
    async def release_resources(self, workflow_id: str) -> None:
        """Release resources allocated to a workflow
        
        Args:
            workflow_id: The ID of the workflow to release resources for
        """
        raise NotImplementedError("Subclasses must implement release_resources()")


class SimpleResourceManager(ResourceManager):
    """Simple resource manager with fixed resource pools"""
    
    def __init__(self, available_resources: Dict[str, int]):
        """Initialize a simple resource manager
        
        Args:
            available_resources: Dictionary mapping resource types to available amounts
                               e.g., {'cpu': 4, 'memory': 8, 'gpu': 1}
        """
        self.available = available_resources.copy()
        self.allocated = {k: 0 for k in available_resources}
        self.workflow_allocations = {}  # Dict[workflow_id, Dict[resource, amount]]
        self.lock = asyncio.Lock()
        
    async def allocate_resources(self, workflow_id: str, requirements: Dict[str, Any]) -> bool:
        """Allocate resources for a workflow
        
        Args:
            workflow_id: The ID of the workflow requesting resources
            requirements: Dictionary of resource requirements
            
        Returns:
            True if resources were successfully allocated, False otherwise
        """
        async with self.lock:
            # Check if workflow already has resources allocated
            if workflow_id in self.workflow_allocations:
                # Already allocated
                return True
                
            # Check if enough resources are available
            for resource, amount in requirements.items():
                if resource not in self.available:
                    return False
                    
                if self.allocated[resource] + amount > self.available[resource]:
                    return False
                    
            # Allocate resources
            allocation = {}
            for resource, amount in requirements.items():
                self.allocated[resource] += amount
                allocation[resource] = amount
                
            # Store the allocation
            self.workflow_allocations[workflow_id] = allocation
            
            return True
            
    async def release_resources(self, workflow_id: str) -> None:
        """Release resources allocated to a workflow
        
        Args:
            workflow_id: The ID of the workflow to release resources for
        """
        async with self.lock:
            # Check if workflow has resources allocated
            if workflow_id not in self.workflow_allocations:
                return
                
            # Release resources
            allocation = self.workflow_allocations[workflow_id]
            for resource, amount in allocation.items():
                self.allocated[resource] -= amount
                
            # Remove the allocation
            del self.workflow_allocations[workflow_id]
            
    async def get_available_resources(self) -> Dict[str, int]:
        """Get currently available resources
        
        Returns:
            Dictionary mapping resource types to available amounts
        """
        async with self.lock:
            return {
                resource: self.available[resource] - self.allocated[resource]
                for resource in self.available
            }


class UserResourceManager(ResourceManager):
    """Resource manager that enforces user-specific quotas"""
    
    def __init__(self, user_id: str, quota_service=None):
        """Initialize a user resource manager
        
        Args:
            user_id: The ID of the user
            quota_service: Optional service for checking quotas
        """
        self.user_id = user_id
        self.quota_service = quota_service
        
        # Example user quota (used if no quota service is provided)
        self.quota = {
            'cpu': 2,
            'memory': 4,
            'workflows': 3,
            'max_duration': 3600  # 1 hour in seconds
        }
        
        # Track allocated resources
        self.allocated = {
            'cpu': 0,
            'memory': 0,
            'workflows': 0
        }
        
        self.workflow_allocations = {}  # Dict[workflow_id, Dict[resource, amount]]
        self.workflow_start_times = {}  # Dict[workflow_id, start_time]
        self.lock = asyncio.Lock()
        
    async def allocate_resources(self, workflow_id: str, requirements: Dict[str, Any]) -> bool:
        """Allocate resources for a workflow based on user quotas
        
        Args:
            workflow_id: The ID of the workflow requesting resources
            requirements: Dictionary of resource requirements
            
        Returns:
            True if resources were successfully allocated, False otherwise
        """
        # If we have a quota service, use it
        if self.quota_service:
            return await self.quota_service.allocate_resources(
                self.user_id, workflow_id, requirements
            )
            
        # Otherwise, use our simple quota implementation
        async with self.lock:
            # Check if workflow already has resources allocated
            if workflow_id in self.workflow_allocations:
                # Already allocated
                return True
                
            # Check workflow count quota
            if self.allocated['workflows'] >= self.quota['workflows']:
                return False
                
            # Check resource quotas
            for resource, amount in requirements.items():
                if resource not in self.quota:
                    continue
                    
                if self.allocated[resource] + amount > self.quota[resource]:
                    return False
                    
            # Allocate resources
            allocation = {}
            for resource, amount in requirements.items():
                if resource in self.allocated:
                    self.allocated[resource] += amount
                    allocation[resource] = amount
                    
            # Increment workflow count
            self.allocated['workflows'] += 1
            
            # Store the allocation and start time
            self.workflow_allocations[workflow_id] = allocation
            self.workflow_start_times[workflow_id] = time.time()
            
            return True
            
    async def release_resources(self, workflow_id: str) -> None:
        """Release resources allocated to a workflow
        
        Args:
            workflow_id: The ID of the workflow to release resources for
        """
        # If we have a quota service, use it
        if self.quota_service:
            await self.quota_service.release_resources(self.user_id, workflow_id)
            return
            
        # Otherwise, use our simple quota implementation
        async with self.lock:
            # Check if workflow has resources allocated
            if workflow_id not in self.workflow_allocations:
                return
                
            # Release resources
            allocation = self.workflow_allocations[workflow_id]
            for resource, amount in allocation.items():
                if resource in self.allocated:
                    self.allocated[resource] -= amount
                    
            # Decrement workflow count
            self.allocated['workflows'] -= 1
            
            # Remove the allocation and start time
            del self.workflow_allocations[workflow_id]
            if workflow_id in self.workflow_start_times:
                del self.workflow_start_times[workflow_id]


class OrganizationResourceManager(ResourceManager):
    """Resource manager for organization-level resource management"""
    
    def __init__(self, org_id: str, quota_service=None):
        """Initialize an organization resource manager
        
        Args:
            org_id: The ID of the organization
            quota_service: Optional service for checking quotas
        """
        self.org_id = org_id
        self.quota_service = quota_service
        
        # Example organization quota (used if no quota service is provided)
        self.quota = {
            'cpu': 16,
            'memory': 32,
            'workflows': 20,
            'gpu': 2
        }
        
        # Track allocated resources
        self.allocated = {
            'cpu': 0,
            'memory': 0,
            'workflows': 0,
            'gpu': 0
        }
        
        self.workflow_allocations = {}  # Dict[workflow_id, Dict[resource, amount]]
        self.lock = asyncio.Lock()
        
    async def allocate_resources(self, workflow_id: str, requirements: Dict[str, Any]) -> bool:
        """Allocate resources for a workflow based on organization quotas
        
        Args:
            workflow_id: The ID of the workflow requesting resources
            requirements: Dictionary of resource requirements
            
        Returns:
            True if resources were successfully allocated, False otherwise
        """
        # If we have a quota service, use it
        if self.quota_service:
            return await self.quota_service.allocate_org_resources(
                self.org_id, workflow_id, requirements
            )
            
        # Otherwise, use our simple quota implementation
        async with self.lock:
            # Check if workflow already has resources allocated
            if workflow_id in self.workflow_allocations:
                # Already allocated
                return True
                
            # Check resource quotas
            for resource, amount in requirements.items():
                if resource not in self.quota:
                    continue
                    
                if self.allocated[resource] + amount > self.quota[resource]:
                    return False
                    
            # Allocate resources
            allocation = {}
            for resource, amount in requirements.items():
                if resource in self.allocated:
                    self.allocated[resource] += amount
                    allocation[resource] = amount
                    
            # Increment workflow count
            self.allocated['workflows'] += 1
            
            # Store the allocation
            self.workflow_allocations[workflow_id] = allocation
            
            return True
            
    async def release_resources(self, workflow_id: str) -> None:
        """Release resources allocated to a workflow
        
        Args:
            workflow_id: The ID of the workflow to release resources for
        """
        # If we have a quota service, use it
        if self.quota_service:
            await self.quota_service.release_org_resources(self.org_id, workflow_id)
            return
            
        # Otherwise, use our simple quota implementation
        async with self.lock:
            # Check if workflow has resources allocated
            if workflow_id not in self.workflow_allocations:
                return
                
            # Release resources
            allocation = self.workflow_allocations[workflow_id]
            for resource, amount in allocation.items():
                if resource in self.allocated:
                    self.allocated[resource] -= amount
                    
            # Decrement workflow count
            self.allocated['workflows'] -= 1
            
            # Remove the allocation
            del self.workflow_allocations[workflow_id]


# Example usage
async def example_usage():
    """Demonstrate how to use resource managers"""
    from orcs.workflow.orchestrator import WorkflowOrchestrator
    from orcs.memory.system import MemorySystem
    from orcs.workflow.models import Workflow
    
    # Create a workflow orchestrator with resource management
    
    # Basic memory system
    memory = MemorySystem()
    
    # Create agent registry (simplified for example)
    agent_registry = {}
    
    # Create a simple resource manager
    resource_manager = SimpleResourceManager({
        'cpu': 4,
        'memory': 8,
        'gpu': 1
    })
    
    # Create the orchestrator with the resource manager
    orchestrator = WorkflowOrchestrator(
        memory_system=memory,
        agent_registry=agent_registry,
        resource_manager=resource_manager
    )
    
    # Create a workflow (simplified for example)
    workflow = Workflow(
        id="workflow1",
        title="Test Workflow",
        description="A test workflow",
        query="Test query"
    )
    
    # Add resource requirements to workflow metadata
    workflow.metadata["resource_requirements"] = {
        'cpu': 2,
        'memory': 4
    }
    
    # Execute the workflow - this will allocate resources
    result = await orchestrator.execute(workflow)
    
    # Resources will be automatically released when the workflow completes
    # (in the orchestrator's finally block)
    
    # Check available resources
    available = await resource_manager.get_available_resources()
    print(f"Available resources after workflow execution: {available}")
    
    # Example with user resource manager
    user_manager = UserResourceManager('user123')
    
    # Create another orchestrator with the user resource manager
    user_orchestrator = WorkflowOrchestrator(
        memory_system=memory,
        agent_registry=agent_registry,
        resource_manager=user_manager
    )
    
    # Execute another workflow using user quotas
    workflow2 = Workflow(
        id="workflow2",
        title="User Workflow",
        description="A workflow with user quotas",
        query="User query"
    )
    
    workflow2.metadata["resource_requirements"] = {
        'cpu': 1,
        'memory': 2
    }
    
    result2 = await user_orchestrator.execute(workflow2)
    
    # User resources will be automatically released as well


if __name__ == "__main__":
    asyncio.run(example_usage()) 