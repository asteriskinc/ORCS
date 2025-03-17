"""
Example implementation of the telemetry hook for multi-tenant deployments.

This module provides examples of how to implement telemetry collectors to 
gather metrics and events for workflows in a multi-tenant deployment.
"""

from typing import Dict, Any, List, Optional
import asyncio
import time
import datetime
import json
import logging


class TelemetryCollector:
    """Base protocol for telemetry collection"""
    
    async def record_event(self, event_type: str, resource_id: str, metadata: Dict[str, Any]) -> None:
        """Record a telemetry event
        
        Args:
            event_type: Type of event (e.g., 'workflow_started', 'task_completed')
            resource_id: ID of the resource that generated the event
            metadata: Additional data about the event
        """
        raise NotImplementedError("Subclasses must implement record_event()")


class LoggingTelemetryCollector(TelemetryCollector):
    """Simple telemetry collector that logs events to a logger"""
    
    def __init__(self, logger=None, log_level=logging.INFO):
        """Initialize a logging telemetry collector
        
        Args:
            logger: Optional logger to use (creates a new one if not provided)
            log_level: Level to log events at
        """
        self.logger = logger or logging.getLogger("orcs.telemetry")
        self.log_level = log_level
        
    async def record_event(self, event_type: str, resource_id: str, metadata: Dict[str, Any]) -> None:
        """Record an event by logging it
        
        Args:
            event_type: Type of event
            resource_id: ID of the resource
            metadata: Additional event data
        """
        event_data = {
            "event_type": event_type,
            "resource_id": resource_id,
            "timestamp": datetime.datetime.now().isoformat(),
            **metadata
        }
        
        self.logger.log(
            self.log_level,
            f"TELEMETRY: {event_type} - {resource_id} - {json.dumps(event_data)}"
        )


class MemoryTelemetryCollector(TelemetryCollector):
    """Telemetry collector that stores events in memory"""
    
    def __init__(self):
        """Initialize a memory telemetry collector"""
        self.events = []
        self.lock = asyncio.Lock()
        
    async def record_event(self, event_type: str, resource_id: str, metadata: Dict[str, Any]) -> None:
        """Record an event in memory
        
        Args:
            event_type: Type of event
            resource_id: ID of the resource
            metadata: Additional event data
        """
        event = {
            "event_type": event_type,
            "resource_id": resource_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "metadata": metadata
        }
        
        async with self.lock:
            self.events.append(event)
            
    async def get_events(self, event_type: Optional[str] = None, resource_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recorded events, optionally filtered
        
        Args:
            event_type: Optional event type to filter by
            resource_id: Optional resource ID to filter by
            
        Returns:
            List of matching events
        """
        async with self.lock:
            filtered_events = self.events
            
            if event_type:
                filtered_events = [e for e in filtered_events if e["event_type"] == event_type]
                
            if resource_id:
                filtered_events = [e for e in filtered_events if e["resource_id"] == resource_id]
                
            return filtered_events
            
    async def clear_events(self) -> None:
        """Clear all recorded events"""
        async with self.lock:
            self.events = []


class UserTelemetryCollector(TelemetryCollector):
    """Telemetry collector that tracks events for a specific user"""
    
    def __init__(self, user_id: str, base_collector: Optional[TelemetryCollector] = None):
        """Initialize a user-specific telemetry collector
        
        Args:
            user_id: The ID of the user
            base_collector: Optional base collector to delegate to
        """
        self.user_id = user_id
        self.base_collector = base_collector or MemoryTelemetryCollector()
        
    async def record_event(self, event_type: str, resource_id: str, metadata: Dict[str, Any]) -> None:
        """Record a user-scoped event
        
        Args:
            event_type: Type of event
            resource_id: ID of the resource
            metadata: Additional event data
        """
        # Add user ID to metadata
        user_metadata = {
            **metadata,
            "user_id": self.user_id
        }
        
        # Delegate to base collector
        await self.base_collector.record_event(event_type, resource_id, user_metadata)


class OrganizationTelemetryCollector(TelemetryCollector):
    """Telemetry collector that tracks events for a specific organization"""
    
    def __init__(self, org_id: str, base_collector: Optional[TelemetryCollector] = None):
        """Initialize an organization-specific telemetry collector
        
        Args:
            org_id: The ID of the organization
            base_collector: Optional base collector to delegate to
        """
        self.org_id = org_id
        self.base_collector = base_collector or MemoryTelemetryCollector()
        
    async def record_event(self, event_type: str, resource_id: str, metadata: Dict[str, Any]) -> None:
        """Record an organization-scoped event
        
        Args:
            event_type: Type of event
            resource_id: ID of the resource
            metadata: Additional event data
        """
        # Add organization ID to metadata
        org_metadata = {
            **metadata,
            "organization_id": self.org_id
        }
        
        # Delegate to base collector
        await self.base_collector.record_event(event_type, resource_id, org_metadata)


class CompoundTelemetryCollector(TelemetryCollector):
    """Telemetry collector that delegates to multiple collectors"""
    
    def __init__(self, collectors: List[TelemetryCollector]):
        """Initialize a compound telemetry collector
        
        Args:
            collectors: List of collectors to delegate to
        """
        self.collectors = collectors
        
    async def record_event(self, event_type: str, resource_id: str, metadata: Dict[str, Any]) -> None:
        """Record an event with all collectors
        
        Args:
            event_type: Type of event
            resource_id: ID of the resource
            metadata: Additional event data
        """
        # Send to all collectors
        await asyncio.gather(
            *[collector.record_event(event_type, resource_id, metadata) 
              for collector in self.collectors]
        )


class MetricAggregator:
    """Aggregates telemetry events into metrics"""
    
    def __init__(self, telemetry_collector: TelemetryCollector):
        """Initialize a metric aggregator
        
        Args:
            telemetry_collector: The collector to get events from
        """
        self.collector = telemetry_collector
        
    async def get_workflow_metrics(self, workflow_id: str) -> Dict[str, Any]:
        """Get metrics for a specific workflow
        
        Args:
            workflow_id: The ID of the workflow
            
        Returns:
            Dictionary of metrics for the workflow
        """
        # Get all events for this workflow
        events = await self.collector.get_events(resource_id=workflow_id)
        
        # Extract start and end times
        start_event = next((e for e in events if e["event_type"] == "workflow_started"), None)
        end_event = next((e for e in events if e["event_type"] in ["workflow_completed", "workflow_failed"]), None)
        
        start_time = None
        end_time = None
        
        if start_event:
            start_time = datetime.datetime.fromisoformat(start_event["timestamp"])
            
        if end_event:
            end_time = datetime.datetime.fromisoformat(end_event["timestamp"])
            
        # Calculate metrics
        metrics = {
            "total_events": len(events),
            "status": "completed" if end_event and end_event["event_type"] == "workflow_completed" else "failed" if end_event else "running"
        }
        
        if start_time and end_time:
            duration = (end_time - start_time).total_seconds()
            metrics["duration"] = duration
            
        # Count events by type
        event_counts = {}
        for event in events:
            event_type = event["event_type"]
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
        metrics["event_counts"] = event_counts
        
        return metrics


# Example usage
async def example_usage():
    """Demonstrate how to use telemetry collectors"""
    from orcs.workflow.orchestrator import WorkflowOrchestrator
    from orcs.memory.system import MemorySystem
    from orcs.workflow.models import Workflow
    
    # Create a workflow orchestrator with telemetry collection
    
    # Basic memory system
    memory = MemorySystem()
    
    # Create agent registry (simplified for example)
    agent_registry = {}
    
    # Create a memory telemetry collector
    telemetry_collector = MemoryTelemetryCollector()
    
    # Create the orchestrator with the telemetry collector
    orchestrator = WorkflowOrchestrator(
        memory_system=memory,
        agent_registry=agent_registry,
        telemetry_collector=telemetry_collector
    )
    
    # Create a workflow (simplified for example)
    workflow = Workflow(
        id="workflow1",
        title="Test Workflow",
        description="A test workflow",
        query="Test query"
    )
    
    # Execute the workflow - this will generate telemetry events
    # (In a real example, tasks would be executed, generating more events)
    result = await orchestrator.execute(workflow)
    
    # Get all recorded events
    events = await telemetry_collector.get_events()
    print(f"Recorded {len(events)} events")
    
    # Get events for a specific workflow
    workflow_events = await telemetry_collector.get_events(resource_id="workflow1")
    print(f"Recorded {len(workflow_events)} events for workflow1")
    
    # Get metrics for the workflow
    aggregator = MetricAggregator(telemetry_collector)
    metrics = await aggregator.get_workflow_metrics("workflow1")
    print(f"Workflow metrics: {metrics}")
    
    # Example with user-specific telemetry
    user_collector = UserTelemetryCollector("user123", telemetry_collector)
    
    # Create another orchestrator with the user telemetry collector
    user_orchestrator = WorkflowOrchestrator(
        memory_system=memory,
        agent_registry=agent_registry,
        telemetry_collector=user_collector
    )
    
    # Execute another workflow
    workflow2 = Workflow(
        id="workflow2",
        title="User Workflow",
        description="A workflow with user telemetry",
        query="User query"
    )
    
    result2 = await user_orchestrator.execute(workflow2)
    
    # Now events for workflow2 will include user_id in metadata


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the example
    asyncio.run(example_usage()) 