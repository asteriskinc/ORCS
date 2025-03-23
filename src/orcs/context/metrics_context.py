from typing import Dict, Any, Optional, List
import logging
import time
from datetime import datetime

from orcs.context.agent_context import AgentContext
from orcs.metrics.context import MetricsContext, BasicMetricsContext

# Set up logger
logger = logging.getLogger("orcs.context.metrics_context")

class MetricsAgentContext(AgentContext):
    """Agent context with metrics capabilities
    
    This extends the base AgentContext to add metrics functionality.
    It implements the full MetricsContext API by delegating to a
    wrapped metrics implementation.
    """
    
    def __init__(self, 
                metrics_impl: Optional[MetricsContext] = None, 
                agent_id: Optional[str] = None, 
                workflow_id: Optional[str] = None):
        """Initialize the metrics agent context
        
        Args:
            metrics_impl: The metrics implementation to use (default: BasicMetricsContext)
            agent_id: ID of the agent (defaults to generated UUID)
            workflow_id: ID of the workflow (defaults to generated UUID)
        """
        super().__init__(agent_id=agent_id, workflow_id=workflow_id)
        
        # Use the provided metrics implementation or create a basic one
        self.metrics = metrics_impl or BasicMetricsContext()
        logger.debug("Initialized MetricsAgentContext with metrics implementation %s", 
                    self.metrics.__class__.__name__)
    
    def record_event(self, event_type: str, resource_id: str, metadata: Dict[str, Any]) -> None:
        """Record an event with metadata
        
        Args:
            event_type: Type of event (e.g., 'agent_start', 'tool_execution')
            resource_id: ID of the resource associated with the event
            metadata: Additional data about the event
        """
        # Add agent and workflow IDs to metadata if not present
        enriched_metadata = metadata.copy()
        if "agent_id" not in enriched_metadata:
            enriched_metadata["agent_id"] = self.agent_id
        if "workflow_id" not in enriched_metadata:
            enriched_metadata["workflow_id"] = self.workflow_id
            
        self.metrics.record_event(event_type, resource_id, enriched_metadata)
    
    def record_metric(self, metric_name: str, value: float, dimensions: Dict[str, str]) -> None:
        """Record a metric value
        
        Args:
            metric_name: Name of the metric
            value: Numeric value of the metric
            dimensions: Dimensions for categorizing the metric
        """
        # Add agent and workflow dimensions if not present
        enriched_dimensions = dimensions.copy()
        if "agent_id" not in enriched_dimensions:
            enriched_dimensions["agent_id"] = self.agent_id
        if "workflow_id" not in enriched_dimensions:
            enriched_dimensions["workflow_id"] = self.workflow_id
            
        self.metrics.record_metric(metric_name, value, enriched_dimensions)
    
    def start_timer(self, timer_name: str, resource_id: str) -> None:
        """Start a timer for measuring duration
        
        Args:
            timer_name: Name of the timer
            resource_id: ID of the resource being timed
        """
        self.metrics.start_timer(timer_name, resource_id)
    
    def stop_timer(self, timer_name: str, resource_id: str) -> float:
        """Stop a timer and return the duration
        
        Args:
            timer_name: Name of the timer
            resource_id: ID of the resource being timed
            
        Returns:
            Duration in seconds
        """
        return self.metrics.stop_timer(timer_name, resource_id)
    
    def get_events(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recorded events
        
        Args:
            event_type: Optional filter for event type
            
        Returns:
            List of recorded events
        """
        if hasattr(self.metrics, "events"):
            if event_type:
                return [e for e in self.metrics.events if e["event_type"] == event_type]
            return self.metrics.events
        return []
    
    def get_metrics(self, metric_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recorded metrics
        
        Args:
            metric_name: Optional filter for metric name
            
        Returns:
            List of recorded metrics
        """
        if hasattr(self.metrics, "metrics"):
            if metric_name:
                return [m for m in self.metrics.metrics if m["metric_name"] == metric_name]
            return self.metrics.metrics
        return [] 